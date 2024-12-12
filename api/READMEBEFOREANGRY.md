- When running flask based api in a docker container using gunicorn, DO NOT IMPORT IT INTO THE app.py OR main.py OR WHATEVER
  because gunicorn will always raise an error bout not finding the "app" inside the "app". Yea, its shitty but we have to put
  up with it :)

- DONT USE JWT LIBRARY, instead use PyJWT (pip install pyjwt), because its newer and actually functions how its supposed to.
  There are issues with classic jwt lib, I dont wanna go to details, just use pyjwt instead, it will save you a lots of time.
  Just make sure that you're using the actual documentation and ask ai for syntx help, because its different from normal jwt lib.
  Plus, make sure after you "pip uninstall jwt" go to "venv/lib/python3.10/site-packages/" and make sure that there isnt a folder 
  named jwt, otherwise itll fuck up your imports and still use the old lib instead of pyjwt. Only when you checked that you can install
  pyjwt ^^
  But when you're launching it inside a docker container, just don't include the jwt in the requerements.txt (req.txt) file, ony PyJWT
