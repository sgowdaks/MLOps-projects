from tasks import long_running_task

print("Sending task to the worker...")

# .delay() is the magic command. 
# It doesn't run the function; it sends a message to Redis.
result = long_running_task.delay("Alice")
# print("result ", type(result)) a class that conatins the task ID and methods to check status or get results later.

print("Task sent! Notice how the script didn't wait 5 seconds.")
print(f"Task ID: {result.id}")

# Wait for the result (optional)
print("Waiting for the result from Redis...")
print(f"Final Message: {result.get()}")