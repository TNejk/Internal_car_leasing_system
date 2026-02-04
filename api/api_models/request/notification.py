from pydantic import BaseModel


# Notifications are gotten by taking role and email from the JWT, there is no request model for them
# A read notification is made by inserting the notifications id into the url:  notifications/{notf_id}
# Then it will return the data
