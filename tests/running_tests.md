# Running Tests

### Setup

Run a mongodb instance locally on port :27017

Make sure you have both pem files in the root level of this repository.
```
private.pem
public.pem
```

### Original routes and v1 routes

Both sets are supported so tests exist for each version, the original routes are tested with test_{testname}, and the versioned routes are test_{version}_{testname}