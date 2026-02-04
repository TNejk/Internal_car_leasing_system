from flask import url_for
def load_icons():
  bell = url_for('static', filename='images/bell.svg')
  user = url_for('static', filename='images/user.svg')
  settings = url_for('static', filename='images/settings.svg')
  house = url_for('static', filename='images/house.svg')
  car = url_for('static', filename='images/car.svg')
  icons = [bell, user, settings, house, car]
  return icons