User docker command:
```shell
docker build . -t rssrocketcontrolcontainer.azurecr.io/rss/flight-management-server
```

Then

```shell
docker login rssrocketcontrolcontainer.azurecr.io
```

and

```shell
docker push rssrocketcontrolcontainer.azurecr.io/rss/flight-management-server
```

Registry docs:
https://learn.microsoft.com/en-us/azure/container-registry/container-registry-get-started-docker-cli?tabs=azure-cli

Environment variables:

```env
FLIGHT_MANAGEMENT_SERVER_CONNECTION_STRING = "[Database connection string]"
FLIGHT_MANAGEMENT_SERVER_DEBUG = "[True/False]"
FLIGHT_MANAGEMENT_SERVER_JWT_AUDIENCE = "[JWT audience]"
```