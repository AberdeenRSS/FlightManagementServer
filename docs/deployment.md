# Deployment

The main branch of this repository is deployed with Github actions.

### Hosting

1. Clone this repository with ```

2. Create ```private.pem``` and ```public.pem``` files in the root directory of this repository

3. Build docker image

```shell
docker build . -t flight-management-server:latest
```

4. Run docker container

```shell
docker run -p 5000:5000 flight-management-server:latest
```

Environment variables:

```env
FLIGHT_MANAGEMENT_SERVER_CONNECTION_STRING = "[Database connection string]"
FLIGHT_MANAGEMENT_SERVER_DEBUG = "[True/False]"
FLIGHT_MANAGEMENT_SERVER_JWT_AUDIENCE = "[JWT audience]"
```