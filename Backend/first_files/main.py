from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from passlib.context import CryptContext
from pydantic import BaseModel
from jose import JWTError, jwt
from datetime import datetime, timedelta
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from nlp_part import preprocess_documents, setup_rag_chat
import boto3
from botocore.exceptions import NoCredentialsError
from dotenv import load_dotenv
import os
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from pydantic import EmailStr

load_dotenv()
UPLOADS_DIR = "uploads"

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")

# s3_client = boto3.client(
#     "s3",
#     aws_access_key_id=AWS_ACCESS_KEY_ID,
#     aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
#     region_name=AWS_REGION,
# )

AWS_BUCKET = 'autogen-rag'
s3 = boto3.resource('s3')
bucket = s3.Bucket(AWS_BUCKET)

# Database setup
DATABASE_URL = "postgresql://manan:assignment@localhost:5432/fastapi_db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Models and schemas
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    confirm_password: str

class UserInDB(UserCreate):
    password_hash: str

class QuestionRequest(BaseModel):
    question: str

# FastAPI app setup
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5175"],  # Adjust to match your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# OAuth2 setup
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Password hashing setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT token setup
SECRET_KEY = "secret-assignment"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Helper function to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Helper function to hash password
def hash_password(password: str):
    return pwd_context.hash(password)

# Helper function to verify password
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# # Helper function to get a user by username
# def get_user_by_username(db, username: str):
#     return db.query(User).filter(User.username == username).first()

# Helper function to get user by either username or email
def get_user_by_username_or_email(db: Session, username: str, email: str = None):
    return db.query(User).filter((User.username == username) | (User.email == email)).first()

# Function to create an access token
def create_access_token(data: dict, expires_delta: timedelta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def upload_vector_store_to_s3(local_folder: str, current_user: str, filename: str) -> None:
    print(f"Starting vector store upload for user {current_user}, file {filename}...")
    base_s3_key = f"{current_user}/{filename}/vector_store"
    for root, _, files in os.walk(local_folder):
        for file in files:
            # Get the full local path
            local_path = os.path.join(root, file)
            
            # Calculate relative path from the base folder
            relative_path = os.path.relpath(local_path, local_folder)
            
            # Create S3 key by joining base key with relative path
            s3_key = f"{base_s3_key}/{relative_path}".replace("\\", "/")
            
            try:
                print(f"Uploading {relative_path} to s3://{bucket.name}/{s3_key}")
                with open(local_path, 'rb') as file_data:
                    bucket.put_object(
                        Key=s3_key,
                        Body=file_data
                    )
                print(f"Successfully uploaded {relative_path}")
            except Exception as e:
                print(f"Error uploading {relative_path}: {str(e)}")
    return
    # s3_key = f"{current_user}/{file.filename}"
    # vector_store_s3_key = f"{current_user}/{file.filename}/vector_store"
    # bucket.put_object(
    #         Key = s3_key, 
    #         Body = contents)
    
    for file, root in os.listdir(local_folder):
        local_file_path = os.path.join(root, file)
        s3_key = os.path.join(s3_base_key, local_file_path)
        print(s3_key)
        try:
            with open(local_file_path, 'rb') as file_data:
                s3_key = os.path.join(s3_base_key,file)
                print(f"s3 key 2: {s3_key}")
                bucket.put_object(Bucket=bucket, Key=s3_key, Body=file_data)
                print(f"Uploaded {local_file_path} to s3://{bucket}/{s3_key}")
        except Exception as e:
            print(f"Failed to upload {local_file_path} to S3: {str(e)}")
    # Walk through the local folder to upload all files recursively
    # for root, _, files in os.walk(local_folder):
    #     for file in files:
    #         local_file_path = os.path.join(root, file)
    #         # Generate S3 key based on the relative file path
    #         s3_key = os.path.join(s3_base_key, os.path.relpath(local_file_path, local_folder))
            
    #         try:
    #             with open(local_file_path, 'rb') as file_data:
    #                 # Upload file to S3
    #                 bucket.put_object(Bucket=bucket, Key=s3_key, Body=file_data)
    #                 print(f"Uploaded {local_file_path} to s3://{bucket}/{s3_key}")
    #         except Exception as e:
    #             print(f"Failed to upload {local_file_path} to S3: {str(e)}")
    
    print("Upload completed.")

# Updated signup route with email and password confirmation
@app.post("/signup", response_model=UserCreate)
def signup(user: UserCreate, db: Session = Depends(get_db)):
    print(f"Received: {user}")
    
    # Check if the passwords match
    if user.password != user.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    db_user = get_user_by_username_or_email(db, user.username, user.email)  # Check both username and email
    if db_user:
        raise HTTPException(status_code=400, detail="Username or Email already registered")
    
    hashed_password = hash_password(user.password)
    db_user = User(username=user.username, email=user.email, password_hash=hashed_password)
    db.add(db_user)
    db.commit()  # Commit to the database
    db.refresh(db_user)  # Refresh the session
    return user

# Updated login route to accept either username or email
@app.post("/token")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    print(f"Username/Email: {form_data.username}, Password: {form_data.password}")
    
    # Check if user exists by username or email
    user = get_user_by_username_or_email(db, form_data.username, form_data.username)
    
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create JWT token
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/protected")
def read_protected_data(token: str = Depends(oauth2_scheme)):
    try:
        # Decode the JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Unauthorized")
        return {"message": f"Hello, {username}! You have accessed protected data."}
    except JWTError:
        raise HTTPException(status_code=401, detail="Unauthorized")
    

# Dependency to get current user
def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Unauthorized")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Unauthorized")

# File upload route
@app.post("/upload")
async def upload_file(file: UploadFile = File(...), current_user: str = Depends(get_current_user)):
    # Process the file
    try:
        print(file.filename)
        contents = await file.read()

        user_upload_dir = os.path.join(UPLOADS_DIR)
        os.makedirs(user_upload_dir, exist_ok=True)
        local_file_path = os.path.join(user_upload_dir, file.filename)
        with open(local_file_path, 'wb') as f:
            f.write(contents)
        print(f"File saved locally to {local_file_path}")
        # file_location = f"uploads/{current_user}/{file.filename}"

        s3_key = f"{current_user}/{file.filename}"
        print(f"key L: {s3_key}")
        

        bucket.put_object(
            Key = s3_key, 
            Body = contents)
        print("buceket me filled")

        # Process the file and create a vector store
        vector_store_path = "vectordb"  # Directory where vector store is saved
        vector_store = preprocess_documents()
        print("aa gaya")
        # Upload the vector store folder to S3
        vector_store_s3_key = f"{current_user}/{file.filename}/vector_store"
        print(f"aa {vector_store_s3_key}")
        upload_vector_store_to_s3(vector_store_path, current_user, file.filename)
        print("back")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": f"File '{file.filename}' uploaded successfully to S3!"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")
    

@app.get("/files/")
def get_file(filename: str, current_user: str = Depends(get_current_user)):
    try:
        # Construct S3 object key
        s3_key = f"{current_user}/{filename}"
        
        # Generate a pre-signed URL for file download
        presigned_url = s3.generate_predesigned_url(
            "get_object",   
            Params={"Bucket": "s3", "Key": s3_key},
            ExpiresIn=3600,  # URL valid for 1 hour
        )
        return {"url": presigned_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve file: {str(e)}")
    

@app.post("/ask")
async def ask_question(
    question_request: QuestionRequest,
    # current_user: str = Depends(get_current_user)
):
    """
    Handle user questions and return RAG-enabled chat responses.
    
    Args:
        question_request: Contains the user's question
        current_user: Current authenticated user
    """
    try:
        # print(f"Received question from user: {current_user}")
        print(f"User's question: {question_request.question}")
        
        # Get the vector store for the current user's document
        print("Loading vector store...")
        embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-mpnet-base-v2",
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
        )
        vector_store = FAISS.load_local("vectordb", embeddings=embeddings, allow_dangerous_deserialization=True)
        print(f"Vector store loaded from 'vectordb'")

        # Set up RAG chat with the vector store
        print("Setting up RAG chat with the vector store...")
        assistant, ragproxyagent = setup_rag_chat(vector_store)
        print("RAG chat setup complete.")
        
        # Initialize chat and get response
        print(f"Initiating chat with message: {question_request.question}")
        chat_result = ragproxyagent.initiate_chat(
            assistant,
            message=question_request.question,
            max_turns=3,
            clear_history=True
        )
        print(f"Chat result received: {chat_result}")
        
        # Extract the last message from the chat result
        if isinstance(chat_result, list) and chat_result:
            response = chat_result[-1].get('content', '')
            print(f"Assistant's response: {response}")
        else:
            response = str(chat_result)
            print(f"Chat result is not a list, raw response: {response}")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "answer": response,
                "success": True
            }
        )
        
    except Exception as e:
        print(f"Error processing question: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing question: {str(e)}"
        )
