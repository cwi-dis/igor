# ca - Certificate Authority

Igor includes a certificate authority implementation that allows local use of SSL communication, and thereby _https:_ access to Igor and devices without using self-signed certificates.

By installing the Igor root certificate on all machines that need access to Igor (or devices) all https accesses become transparent to the user (and to automatic scripts, and Igor itself).

the _ca_ plugin is only a frontend (and UI) to the _igorCA_ command line tool. In turn, that tool is only a front end op the _openssl_ command which does all the heavy lifting of generating keys, certificate signing requests, certificates, etc.

## schema

* `plugindata/ca/ca`: if non-empty this should be the URL for the Igor that this Igor uses as its CA. If empty (or if it doesn't exist) this Igor is its own CA.

## Using Igor ca certificates

This section assumes the CA is already initialized and Igor is configured for using a ca-signed certificate (see below for instructions).

To install the root certificate chain on your machine download it through Igor, from _/plugin/ca/root_. This may be accessible as <http://igor.local:9333/plugin/ca/root> or <https://igor.local:9333/plugin/ca/root>. In the second case you will have to accept the Igor certificate once (because it isn't trusted yet, because you have not installed the root certificate yet).

### MacOS

On MacOS, open the certificate in _Keychain Access_. Add it to the _login_ keychain or the _System_ keychain (the latter installs it for all users on the system). Select the newly-installed certificate, open it, open the _Trust_ section and set _X.509 Basic Policy_ to _Always Trust_.

### Linux

On Linux, rename the certificate so that it has a _.crt_ extension. Copy it into _/usr/share/ca-certificates_. Run _update-ca-certificates_. The latter two steps may have to be done using _sudo_. Maybe (unsure when) you have to run `dpkg-reconfigure ca-certificates` in stead of the update command and select your new certificate.

### Windows

To be provided.

### Checking that it worked

After installing the certificate you can check that it worked by pointing your browser at _https://igor.local:9333_ or (even better, because you previously manually trusted the igor certificate) use some other tool that uses SSL access, for example

```
curl https://igor.local:9333
```

## Initializing the ca

To initialize the Certificate Authority run

```
igorCA initialize
```
This creates a root key and certificate (you get to supply all the details such as country and organization and such). The root key is protected by a password (which you supply). After the initialize command is finished you can remove the root key and certificate (from _~/.igor/ca/root_) and keep them offline, if you want, for added security. You only need them again if your system has been compromised.

Next it creates an intermediate key and certificate (supply identical details as for the root) and signs it with the root key. This intermediate key is not password-protected, and will be used for normal signing operations. The root and intermediate certificates are concatenated for installation in other systems (see previous section) so that trust can be established.

All infrastructure is kept in _~/.igor/ca_. Revocation is not implemented yet but possible.

## Enabling https for Igor

After the CA has been initialized the following command will create a key and certificate for Igor itself:

```
igorCA self
```

This creates a private key _~/.igor/igor.key_ and a Certificate Signing Request _~/.igor/igor.csr_ and uses the CA to sign that, giving a certificate _~/.igor/igor.crt_.

At startup, the existence of _~/.igor/igor.key_ and _~/.igor/igor.crt_ will cause Igor to serve on _https_ in stead of _http_ (but still on the default _9333_ port).

## Enabling https for other services

To create a secret key and certificate for a service _foo_ (name for your personal enjoyment only) listening to addresses _foo.local_ and _192.168.4.1_ (names externally visible) run the following command in some temporary directory:

```
igorCA gen foo foo.local 192.168.4.1
```

This creates a number of files in the current directory: _foo.key_ and _foo.crt_ are the key and certificate. Copy these to the service. The other files (_foo.csr_ and _foo.csrconfig_) are temporary files.

## Using igorCA on a different machine

The `igorCA` command will normally use local filesystem access to obtain keys and certificates for signing, but it can also use the _ca plugin_ as an intermediate to do the actual signing.

The command line to sign a key for a local igor server, using a master igor as the CA:

```
igorCA --remote --url https://masterigor.local:9333/data/ self
```
And the command line to sign a key for a service _foo_ using the default Igor:

```
igorCA --remote gen foo foo.local 192.168.4.1
```
