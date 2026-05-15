from celery import Celery
import time

# 1. Initialize Celery (The Manager)
# We tell it to use Redis as the 'Order Rail' (broker) and the 'Cabinet' (backend)
app = Celery('my_experiment', 
             broker='redis://localhost:6379/0',
             backend='redis://localhost:6379/0')

@app.task
def long_running_task(name):
    print(f"Started processing {name}...")
    # Simulate a heavy job (like resizing an image or complex math)
    time.sleep(5) 
    print(f"Finished processing {name}!")
    return f"Hello, {name}! Task Complete."