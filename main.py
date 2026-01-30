from zenml import step, pipeline


@step
def hello() -> str:
    """Prints 'Hello from ZenML!'"""
    return "Hello from ZenML!"


@step
def print_output(message: str) -> None:
    """Prints the message"""
    print(message)


@pipeline(name="hello-world", enable_cache=True)
def hello_world_pipeline() -> None:
    """A pipeline that says hello"""
    msg = hello()
    print_output(msg)


if __name__ == "__main__":
    hello_world_pipeline()
