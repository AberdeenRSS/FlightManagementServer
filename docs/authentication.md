# Authentication system

In general the authentication system is build according to the [OAuth2 standard](https://oauth.net/2/). There are different authentication flows
available which all return a jwt token that can then be used by the client to authorize and identify themselves on every request. As the jwt
token is cryptographically signed it doesn't depend on the serer to hold session information, etc. This makes the everything more resilliant (e.g. 
in case of restarts), faster (no db operations needed to retrieve session info) and verifiable from outside (signature of the token can be
verified by any party).

## Authentication flows

### Username/Password

Users can create a user account on the server. This happens by providing a username (email) and a password which gets stored
securely in the database (hashed and salted). The user can then log in with these credential to obtain a jwt token as well
as a refresh token. 
The refresh token can be used with the authorization code grant flow as they are a form of single use authorization codes.
It is single use and has a limited lifetime. Having a refresh token
enables the client to re-authenticate at a later point in time, without the password having to be stored (e.g. in the browser
local storage or similar).

### Authorization Code Grant

Codes are stored in the database. They have a limited life time (length dependent on what token it is). They belong
to a specific user. To log in with a token the token is simply send to the server and the server sends back a
jwt token.


## Types of users

There are currently two types of users:

### Web interface users (human users)

Use the Username/Password flow. Enables permission based access to resources like vessels and flights.

### Vessels

Use the token auth flow