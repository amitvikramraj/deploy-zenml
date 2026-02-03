from zenml import step, pipeline
from zenml.config import DeploymentSettings


@step
def hello() -> str:
    """Prints 'Hello from ZenML!'"""
    return "Hello from ZenML!"


@step
def print_output(message: str) -> None:
    """Prints the message"""
    print(message)


# DeploymentSettings: see https://docs.zenml.io/concepts/deployment/deployment_settings
# - timeout_keep_alive: reduce RemoteDisconnected when CLI polls for status (long-lived connections)
# - uvicorn_port=8000: matches default invoke URL http://127.0.0.1:8000
deploy_settings = DeploymentSettings(
    uvicorn_host="0.0.0.0",
    uvicorn_port=8000,
    uvicorn_kwargs={
        "timeout_keep_alive": 120,  # seconds; long polls for deployment status
    },
)


@pipeline(
    name="hello-world",
    enable_cache=False,
    settings={"deployment": deploy_settings},
)
def hello_world_pipeline() -> None:
    """A pipeline that says hello"""
    msg = hello()
    print_output(msg)


if __name__ == "__main__":
    hello_world_pipeline()
