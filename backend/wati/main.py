from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import database
from .routes import user,broadcast,contacts,auth,woocommerce,integration
from .services import dramatiq_router
from . import oauth2
# models creation
database.Base.metadata.create_all(bind=database.engine)

app = FastAPI()

# adding the routes

app.include_router(broadcast.router)
app.include_router(contacts.router)
app.include_router(user.router)
app.include_router(auth.router)
app.include_router(oauth2.router)
app.include_router(dramatiq_router.router)
app.include_router(woocommerce.router)
app.include_router(integration.router)

# defining origin for cors



# CORS middleware configuration
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # Adjust this to specific origins in production
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )




app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

 









     
