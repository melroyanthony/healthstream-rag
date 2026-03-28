"""AWS Lambda handler using Mangum adapter."""

from mangum import Mangum

from app.api.main import app

handler = Mangum(app, lifespan="off")
