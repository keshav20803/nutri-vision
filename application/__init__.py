from flask import Flask
from flask_pymongo import PyMongo
from pymongo import MongoClient
import os

app=Flask(__name__)
app.config["SECRET_KEY"]=os.getenv("SECRET_KEY")
client = MongoClient(os.getenv("MONGODB_CLIENT"))
db=client.nutrients_app

from application import routes