from flask import url_for
def load_icons():
  bell = url_for('static', filename='sources/images/bell.svg')
  user = url_for('static', filename='sources/images/user.svg')
  settings = url_for('static', filename='sources/images/settings.svg')
  house = url_for('static', filename='sources/images/house.svg')
  car = url_for('static', filename='sources/images/car.svg')
  icons = [bell, user, settings, house, car]
  return icons