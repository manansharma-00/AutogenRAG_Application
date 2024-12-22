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
import boto3
from dotenv import load_dotenv
import os
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from pydantic import EmailStr
from unstructured_nlp import DocumentProcessor, RAGChatManager

load_dotenv()
UPLOADS_DIR = "uploads"

# AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
# AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
# AWS_REGION = os.getenv("AWS_REGION")


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

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_user_by_username_or_email(db: Session, username: str, email: str = None):
    return db.query(User).filter((User.username == username) | (User.email == email)).first()


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
            local_path = os.path.join(root, file)
            relative_path = os.path.relpath(local_path, local_folder)
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

        processor = DocumentProcessor(uploads_dir=user_upload_dir)
        print("done1")
        documents = processor.process_documents()
        
        if not documents:
            raise ValueError("No content could be extracted from the document")
        
        # Create chunks
        chunks = processor.create_chunks(documents)
        
        # Create embeddings
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-mpnet-base-v2",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        
        # Create and save vector store
        vector_store = FAISS.from_documents(chunks, embeddings)
        print("vs bana")
        vector_store_path = os.path.join("vectordb")
        # os.makedirs(os.path.dirname(vector_store_path), exist_ok=True)
        vector_store.save_local("vectordb")
        print("vs save")
        
        # Upload vector store to S3
        vector_store_s3_key = f"{current_user}/{file.filename}/vector_store"
        upload_vector_store_to_s3(vector_store_path, current_user, file.filename)
        
        # Clean up local files
        if os.path.exists(local_file_path):
            os.remove(local_file_path)
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": f"File '{file.filename}' processed and uploaded successfully!",
                "extracted_chunks": len(chunks)
            }
        )
        
    except Exception as e:
        if os.path.exists(local_file_path):
            os.remove(local_file_path)
        raise HTTPException(status_code=500, detail=f"File processing failed: {str(e)}")
    

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
def ask_question(
    question_request: QuestionRequest,
):
    """
    Handle user questions and return RAG-enabled chat responses.
    
    Args:
        question_request: Contains the user's question
        current_user: Current authenticated user
    """
    try:
        # Initialize the RAG chat manager
        rag_manager = RAGChatManager(
            vector_store_base_path="vectordb",
            config_list=[
                {
                    'model': 'gpt-3.5-turbo',
                    'api_key': "",
                }
            ]
        )
        
        # Start the chat
        chat_result = rag_manager.start_chat(
            question=question_request.question
        )
        
        return {
            "status": "success",
            "result": chat_result
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")