import time
def sleep_replacement(seconds):
    start_time = time.time()  # Record the current time
    while time.time() - start_time < seconds:
        pass  # Keep looping until the time difference reaches the desired seconds



while True:
    print("sdsd")
    sleep_replacement(30)