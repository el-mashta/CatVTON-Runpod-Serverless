BuildKit


## Overview

[BuildKit](https://github.com/moby/buildkit)
is an improved backend to replace the legacy builder. BuildKit is the default builder
for users on Docker Desktop, and Docker Engine as of version 23.0.

BuildKit provides new functionality and improves your builds' performance.
It also introduces support for handling more complex scenarios:

- Detect and skip executing unused build stages
- Parallelize building independent build stages
- Incrementally transfer only the changed files in your
  [build context](../concepts/context.md) between builds
- Detect and skip transferring unused files in your
  [build context](../concepts/context.md)
- Use [Dockerfile frontend](frontend.md) implementations with many
  new features
- Avoid side effects with rest of the API (intermediate images and containers)
- Prioritize your build cache for automatic pruning

Apart from many new features, the main areas BuildKit improves on the current
experience are performance, storage management, and extensibility. From the
performance side, a significant update is a new fully concurrent build graph
solver. It can run build steps in parallel when possible and optimize out
commands that don't have an impact on the final result.
The access to the local source files has also been optimized. By tracking
only the updates made to these
files between repeated build invocations, there is no need to wait for local
files to be read or uploaded before the work can begin.

## LLB

At the core of BuildKit is a
[Low-Level Build (LLB)](https://github.com/moby/buildkit#exploring-llb) definition format. LLB is an intermediate binary format
that allows developers to extend BuildKit. LLB defines a content-addressable
dependency graph that can be used to put together complex build
definitions. It also supports features not exposed in Dockerfiles, like direct
data mounting and nested invocation.

{{< figure src="../images/buildkit-dag.svg" class="invertible" >}}

Everything about execution and caching of your builds is defined in LLB. The
caching model is entirely rewritten compared to the legacy builder. Rather than
using heuristics to compare images, LLB directly tracks the checksums of build
graphs and content mounted to specific operations. This makes it much faster,
more precise, and portable. The build cache can even be exported to a registry,
where it can be pulled on-demand by subsequent invocations on any host.

LLB can be generated directly using a
[golang client package](https://pkg.go.dev/github.com/moby/buildkit/client/llb) that allows defining the relationships between your
build operations using Go language primitives. This gives you full power to run
anything you can imagine, but will probably not be how most people will define
their builds. Instead, most users would use a frontend component, or LLB nested
invocation, to run a prepared set of build steps.

## Frontend

A frontend is a component that takes a human-readable build format and converts
it to LLB so BuildKit can execute it. Frontends can be distributed as images,
and the user can target a specific version of a frontend that is guaranteed to
work for the features used by their definition.

For example, to build a [Dockerfile](/reference/dockerfile.md) with
BuildKit, you would
[use an external Dockerfile frontend](frontend.md).

## Getting started

BuildKit is the default builder for users on Docker Desktop and Docker Engine
v23.0 and later.

If you have installed Docker Desktop, you don't need to enable BuildKit. If you
are running a version of Docker Engine version earlier than 23.0, you can enable
BuildKit either by setting an environment variable, or by making BuildKit the
default setting in the daemon configuration.

To set the BuildKit environment variable when running the `docker build`
command, run:

```console
$ DOCKER_BUILDKIT=1 docker build .
```

> [!NOTE]
>
> Buildx always uses BuildKit.

To use Docker BuildKit by default, edit the Docker daemon configuration in
`/etc/docker/daemon.json` as follows, and restart the daemon.

```json
{
  "features": {
    "buildkit": true
  }
}
```

If the `/etc/docker/daemon.json` file doesn't exist, create new file called
`daemon.json` and then add the following to the file. And restart the Docker
daemon.

## BuildKit on Windows

> [!WARNING]
>
> BuildKit only fully supports building Linux containers. Windows container
> support is experimental.

BuildKit has experimental support for Windows containers (WCOW) as of version 0.13.
This section walks you through the steps for trying it out.
To share feedback, [open an issue in the repository](https://github.com/moby/buildkit/issues/new), especially `buildkitd.exe`.

### Known limitations

For information about open bugs and limitations related to BuildKit on Windows,
see [GitHub issues](https://github.com/moby/buildkit/issues?q=is%3Aissue%20state%3Aopen%20label%3Aarea%2Fwindows-wcow).

### Prerequisites

- Architecture: `amd64`, `arm64` (binaries available but not officially tested yet).
- Supported OS: Windows Server 2019, Windows Server 2022, Windows 11.
- Base images: `ServerCore:ltsc2019`, `ServerCore:ltsc2022`, `NanoServer:ltsc2022`.
  See the [compatibility map here](https://learn.microsoft.com/en-us/virtualization/windowscontainers/deploy-containers/version-compatibility?tabs=windows-server-2019%2Cwindows-11#windows-server-host-os-compatibility).
- Docker Desktop version 4.29 or later

### Steps

> [!NOTE]
>
> The following commands require administrator (elevated) privileges in a PowerShell terminal.

1. Enable the **Hyper-V** and **Containers** Windows features.

   ```console
   > Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V, Containers -All
   ```

   If you see `RestartNeeded` as `True`, restart your machine and re-open a PowerShell terminal as an administrator.
   Otherwise, continue with the next step.

2. Switch to Windows containers in Docker Desktop.

   Select the Docker icon in the taskbar, and then **Switch to Windows containers...**.

3. Install containerd version 1.7.7 or later following the setup instructions [here](https://github.com/containerd/containerd/blob/main/docs/getting-started.md#installing-containerd-on-windows).

4. Download and extract the latest BuildKit release.

   ```powershell
   $version = "v0.22.0" # specify the release version, v0.13+
   $arch = "amd64" # arm64 binary available too
   curl.exe -LO https://github.com/moby/buildkit/releases/download/$version/buildkit-$version.windows-$arch.tar.gz
   # there could be another `.\bin` directory from containerd instructions
   # you can move those
   mv bin bin2
   tar.exe xvf .\buildkit-$version.windows-$arch.tar.gz
   ## x bin/
   ## x bin/buildctl.exe
   ## x bin/buildkitd.exe
   ```

5. Install BuildKit binaries on `PATH`.

   ```powershell
   # after the binaries are extracted in the bin directory
   # move them to an appropriate path in your $Env:PATH directories or:
   Copy-Item -Path ".\bin" -Destination "$Env:ProgramFiles\buildkit" -Recurse -Force
   # add `buildkitd.exe` and `buildctl.exe` binaries in the $Env:PATH
   $Path = [Environment]::GetEnvironmentVariable("PATH", "Machine") + `
       [IO.Path]::PathSeparator + "$Env:ProgramFiles\buildkit"
   [Environment]::SetEnvironmentVariable( "Path", $Path, "Machine")
   $Env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + `
       [System.Environment]::GetEnvironmentVariable("Path","User")
   ```
6. Start the BuildKit daemon.

   ```console
   > buildkitd.exe
   ```
   > [!NOTE]
   > If you are running a _dockerd-managed_ `containerd` process, use that instead, by supplying the address:
   > `buildkitd.exe --containerd-worker-addr "npipe:////./pipe/docker-containerd"`

7. In another terminal with administrator privileges, create a remote builder that uses the local BuildKit daemon.

   > [!NOTE]
   >
   > This requires Docker Desktop version 4.29 or later.

   ```console
   > docker buildx create --name buildkit-exp --use --driver=remote npipe:////./pipe/buildkitd
   buildkit-exp
   ```

8. Verify the builder connection by running `docker buildx inspect`.

   ```console
   > docker buildx inspect
   ```

   The output should indicate that the builder platform is Windows,
   and that the endpoint of the builder is a named pipe.

   ```text
   Name:          buildkit-exp
    Driver:        remote
    Last Activity: 2024-04-15 17:51:58 +0000 UTC
    Nodes:
    Name:             buildkit-exp0
    Endpoint:         npipe:////./pipe/buildkitd
    Status:           running
    BuildKit version: v0.13.1
    Platforms:        windows/amd64
   ...
   ```

9. Create a Dockerfile and build a `hello-buildkit` image.

   ```console
   > mkdir sample_dockerfile
   > cd sample_dockerfile
   > Set-Content Dockerfile @"
   FROM mcr.microsoft.com/windows/nanoserver:ltsc2022
   USER ContainerAdministrator
   COPY hello.txt C:/
   RUN echo "Goodbye!" >> hello.txt
   CMD ["cmd", "/C", "type C:\\hello.txt"]
   "@
   Set-Content hello.txt @"
   Hello from BuildKit!
   This message shows that your installation appears to be working correctly.
   "@
   ```

10. Build and push the image to a registry.

    ```console
    > docker buildx build --push -t <username>/hello-buildkit .
    ```

11. After pushing to the registry, run the image with `docker run`.

    ```console
    > docker run <username>/hello-buildkit
    ```



- [buildkitd.toml](https://docs.docker.com/build/buildkit/toml-configuration/)

- [Configure BuildKit](https://docs.docker.com/build/buildkit/configure/)

- [Custom Dockerfile syntax](https://docs.docker.com/build/buildkit/frontend/)

- [Dockerfile release notes](https://docs.docker.com/build/buildkit/dockerfile-release-notes/)

buildkitd.toml


The TOML file used to configure the buildkitd daemon settings has a short
list of global settings followed by a series of sections for specific areas
of daemon configuration.

The file path is `/etc/buildkit/buildkitd.toml` for rootful mode,
`~/.config/buildkit/buildkitd.toml` for rootless mode.

The following is a complete `buildkitd.toml` configuration example.
Note that some configuration options are only useful in edge cases.

```toml
# debug enables additional debug logging
debug = true
# trace enables additional trace logging (very verbose, with potential performance impacts)
trace = true
# root is where all buildkit state is stored.
root = "/var/lib/buildkit"
# insecure-entitlements allows insecure entitlements, disabled by default.
insecure-entitlements = [ "network.host", "security.insecure", "device" ]

[log]
  # log formatter: json or text
  format = "text"

[dns]
  nameservers=["1.1.1.1","8.8.8.8"]
  options=["edns0"]
  searchDomains=["example.com"]

[grpc]
  address = [ "tcp://0.0.0.0:1234" ]
  # debugAddress is address for attaching go profiles and debuggers.
  debugAddress = "0.0.0.0:6060"
  uid = 0
  gid = 0
  [grpc.tls]
    cert = "/etc/buildkit/tls.crt"
    key = "/etc/buildkit/tls.key"
    ca = "/etc/buildkit/tlsca.crt"

[otel]
  # OTEL collector trace socket path
  socketPath = "/run/buildkit/otel-grpc.sock"

[cdi]
  # Disables support of the Container Device Interface (CDI).
  disabled = true
  # List of directories to scan for CDI spec files. For more details about CDI
  # specification, please refer to https://github.com/cncf-tags/container-device-interface/blob/main/SPEC.md#cdi-json-specification
  specDirs = ["/etc/cdi", "/var/run/cdi", "/etc/buildkit/cdi"]

# config for build history API that stores information about completed build commands
[history]
  # maxAge is the maximum age of history entries to keep, in seconds.
  maxAge = 172800
  # maxEntries is the maximum number of history entries to keep.
  maxEntries = 50

[worker.oci]
  enabled = true
  # platforms is manually configure platforms, detected automatically if unset.
  platforms = [ "linux/amd64", "linux/arm64" ]
  snapshotter = "auto" # overlayfs or native, default value is "auto".
  rootless = false # see docs/rootless.md for the details on rootless mode.
  # Whether run subprocesses in main pid namespace or not, this is useful for
  # running rootless buildkit inside a container.
  noProcessSandbox = false
  # gc enables/disables garbage collection
  gc = true
  # reservedSpace is the minimum amount of disk space guaranteed to be
  # retained by this buildkit worker - any usage below this threshold will not
  # be reclaimed during garbage collection.
  # all disk space parameters can be an integer number of bytes (e.g.
  # 512000000), a string with a unit (e.g. "512MB"), or a string percentage
  # of the total disk space (e.g. "10%")
  reservedSpace = "30%"
  # maxUsedSpace is the maximum amount of disk space that may be used by
  # this buildkit worker - any usage above this threshold will be reclaimed
  # during garbage collection.
  maxUsedSpace = "60%"
  # minFreeSpace is the target amount of free disk space that the garbage
  # collector will attempt to leave - however, it will never be bought below
  # reservedSpace.
  minFreeSpace = "20GB"
  # alternate OCI worker binary name(example 'crun'), by default either 
  # buildkit-runc or runc binary is used
  binary = ""
  # name of the apparmor profile that should be used to constrain build containers.
  # the profile should already be loaded (by a higher level system) before creating a worker.
  apparmor-profile = ""
  # limit the number of parallel build steps that can run at the same time
  max-parallelism = 4
  # maintain a pool of reusable CNI network namespaces to amortize the overhead
  # of allocating and releasing the namespaces
  cniPoolSize = 16

  [worker.oci.labels]
    "foo" = "bar"

  [[worker.oci.gcpolicy]]
    # reservedSpace is the minimum amount of disk space guaranteed to be
    # retained by this policy - any usage below this threshold will not be
    # reclaimed during # garbage collection.
    reservedSpace = "512MB"
    # maxUsedSpace is the maximum amount of disk space that may be used by this
    # policy - any usage above this threshold will be reclaimed during garbage
    # collection.
    maxUsedSpace = "1GB"
    # minFreeSpace is the target amount of free disk space that the garbage
    # collector will attempt to leave - however, it will never be bought below
    # reservedSpace.
    minFreeSpace = "10GB"
    # keepDuration can be an integer number of seconds (e.g. 172800), or a
    # string duration (e.g. "48h")
    keepDuration = "48h"
    filters = [ "type==source.local", "type==exec.cachemount", "type==source.git.checkout"]
  [[worker.oci.gcpolicy]]
    all = true
    reservedSpace = 1024000000

[worker.containerd]
  address = "/run/containerd/containerd.sock"
  enabled = true
  platforms = [ "linux/amd64", "linux/arm64" ]
  namespace = "buildkit"

  # gc enables/disables garbage collection
  gc = true
  # reservedSpace is the minimum amount of disk space guaranteed to be
  # retained by this buildkit worker - any usage below this threshold will not
  # be reclaimed during garbage collection.
  # all disk space parameters can be an integer number of bytes (e.g.
  # 512000000), a string with a unit (e.g. "512MB"), or a string percentage
  # of the total disk space (e.g. "10%")
  reservedSpace = "30%"
  # maxUsedSpace is the maximum amount of disk space that may be used by
  # this buildkit worker - any usage above this threshold will be reclaimed
  # during garbage collection.
  maxUsedSpace = "60%"
  # minFreeSpace is the target amount of free disk space that the garbage
  # collector will attempt to leave - however, it will never be bought below
  # reservedSpace.
  minFreeSpace = "20GB"
  # limit the number of parallel build steps that can run at the same time
  max-parallelism = 4
  # maintain a pool of reusable CNI network namespaces to amortize the overhead
  # of allocating and releasing the namespaces
  cniPoolSize = 16
  # defaultCgroupParent sets the parent cgroup of all containers.
  defaultCgroupParent = "buildkit"

  [worker.containerd.labels]
    "foo" = "bar"

  # configure the containerd runtime
  [worker.containerd.runtime]
    name = "io.containerd.runc.v2"
    path = "/path/to/containerd/runc/shim"
    options = { BinaryName = "runc" }

  [[worker.containerd.gcpolicy]]
    reservedSpace = 512000000
    keepDuration = 172800
    filters = [ "type==source.local", "type==exec.cachemount", "type==source.git.checkout"]
  [[worker.containerd.gcpolicy]]
    all = true
    reservedSpace = 1024000000

# registry configures a new Docker register used for cache import or output.
[registry."docker.io"]
  # mirror configuration to handle path in case a mirror registry requires a /project path rather than just a host:port
  mirrors = ["yourmirror.local:5000", "core.harbor.domain/proxy.docker.io"]
  # Use plain HTTP to connect to the mirrors.
  http = true
  # Use HTTPS with self-signed certificates. Do not enable this together with `http`.
  insecure = true
  ca=["/etc/config/myca.pem"]
  [[registry."docker.io".keypair]]
    key="/etc/config/key.pem"
    cert="/etc/config/cert.pem"

# optionally mirror configuration can be done by defining it as a registry.
[registry."yourmirror.local:5000"]
  http = true

# Frontend control
[frontend."dockerfile.v0"]
  enabled = true

[frontend."gateway.v0"]
  enabled = true
  # If allowedRepositories is empty, all gateway sources are allowed.
  # Otherwise, only the listed repositories are allowed as a gateway source.
  # 
  # NOTE: Only the repository name (without tag) is compared.
  #
  # Example:
  # allowedRepositories = [ "docker-registry.wikimedia.org/repos/releng/blubber/buildkit" ]
  allowedRepositories = []

[system]
  # how often buildkit scans for changes in the supported emulated platforms
  platformsCacheMaxAge = "1h"
```

Configure BuildKit


If you create a `docker-container` or `kubernetes` builder with Buildx, you can
apply a custom [BuildKit configuration](toml-configuration.md) by passing the
[`--buildkitd-config` flag](/reference/cli/docker/buildx/create.md#buildkitd-config)
to the `docker buildx create` command.

## Registry mirror

You can define a registry mirror to use for your builds. Doing so redirects
BuildKit to pull images from a different hostname. The following steps exemplify
defining a mirror for `docker.io` (Docker Hub) to `mirror.gcr.io`.

1. Create a TOML at `/etc/buildkitd.toml` with the following content:

   ```toml
   debug = true
   [registry."docker.io"]
     mirrors = ["mirror.gcr.io"]
   ```

   > [!NOTE]
   >
   > `debug = true` turns on debug requests in the BuildKit daemon, which logs a
   > message that shows when a mirror is being used.

2. Create a `docker-container` builder that uses this BuildKit configuration:

   ```console
   $ docker buildx create --use --bootstrap \
     --name mybuilder \
     --driver docker-container \
     --buildkitd-config /etc/buildkitd.toml
   ```

3. Build an image:

   ```bash
   docker buildx build --load . -f - <<EOF
   FROM alpine
   RUN echo "hello world"
   EOF
   ```

The BuildKit logs for this builder now shows that it uses the GCR mirror. You
can tell by the fact that the response messages include the `x-goog-*` HTTP
headers.

```console
$ docker logs buildx_buildkit_mybuilder0
```

```text
...
time="2022-02-06T17:47:48Z" level=debug msg="do request" request.header.accept="application/vnd.docker.container.image.v1+json, */*" request.header.user-agent=containerd/1.5.8+unknown request.method=GET spanID=9460e5b6e64cec91 traceID=b162d3040ddf86d6614e79c66a01a577
time="2022-02-06T17:47:48Z" level=debug msg="fetch response received" response.header.accept-ranges=bytes response.header.age=1356 response.header.alt-svc="h3=\":443\"; ma=2592000,h3-29=\":443\"; ma=2592000,h3-Q050=\":443\"; ma=2592000,h3-Q046=\":443\"; ma=2592000,h3-Q043=\":443\"; ma=2592000,quic=\":443\"; ma=2592000; v=\"46,43\"" response.header.cache-control="public, max-age=3600" response.header.content-length=1469 response.header.content-type=application/octet-stream response.header.date="Sun, 06 Feb 2022 17:25:17 GMT" response.header.etag="\"774380abda8f4eae9a149e5d5d3efc83\"" response.header.expires="Sun, 06 Feb 2022 18:25:17 GMT" response.header.last-modified="Wed, 24 Nov 2021 21:07:57 GMT" response.header.server=UploadServer response.header.x-goog-generation=1637788077652182 response.header.x-goog-hash="crc32c=V3DSrg==" response.header.x-goog-hash.1="md5=d0OAq9qPTq6aFJ5dXT78gw==" response.header.x-goog-metageneration=1 response.header.x-goog-storage-class=STANDARD response.header.x-goog-stored-content-encoding=identity response.header.x-goog-stored-content-length=1469 response.header.x-guploader-uploadid=ADPycduqQipVAXc3tzXmTzKQ2gTT6CV736B2J628smtD1iDytEyiYCgvvdD8zz9BT1J1sASUq9pW_ctUyC4B-v2jvhIxnZTlKg response.status="200 OK" spanID=9460e5b6e64cec91 traceID=b162d3040ddf86d6614e79c66a01a577
time="2022-02-06T17:47:48Z" level=debug msg="fetch response received" response.header.accept-ranges=bytes response.header.age=760 response.header.alt-svc="h3=\":443\"; ma=2592000,h3-29=\":443\"; ma=2592000,h3-Q050=\":443\"; ma=2592000,h3-Q046=\":443\"; ma=2592000,h3-Q043=\":443\"; ma=2592000,quic=\":443\"; ma=2592000; v=\"46,43\"" response.header.cache-control="public, max-age=3600" response.header.content-length=1471 response.header.content-type=application/octet-stream response.header.date="Sun, 06 Feb 2022 17:35:13 GMT" response.header.etag="\"35d688bd15327daafcdb4d4395e616a8\"" response.header.expires="Sun, 06 Feb 2022 18:35:13 GMT" response.header.last-modified="Wed, 24 Nov 2021 21:07:12 GMT" response.header.server=UploadServer response.header.x-goog-generation=1637788032100793 response.header.x-goog-hash="crc32c=aWgRjA==" response.header.x-goog-hash.1="md5=NdaIvRUyfar8201DleYWqA==" response.header.x-goog-metageneration=1 response.header.x-goog-storage-class=STANDARD response.header.x-goog-stored-content-encoding=identity response.header.x-goog-stored-content-length=1471 response.header.x-guploader-uploadid=ADPycdtR-gJYwC7yHquIkJWFFG8FovDySvtmRnZBqlO3yVDanBXh_VqKYt400yhuf0XbQ3ZMB9IZV2vlcyHezn_Pu3a1SMMtiw response.status="200 OK" spanID=9460e5b6e64cec91 traceID=b162d3040ddf86d6614e79c66a01a577
time="2022-02-06T17:47:48Z" level=debug msg=fetch spanID=9460e5b6e64cec91 traceID=b162d3040ddf86d6614e79c66a01a577
time="2022-02-06T17:47:48Z" level=debug msg=fetch spanID=9460e5b6e64cec91 traceID=b162d3040ddf86d6614e79c66a01a577
time="2022-02-06T17:47:48Z" level=debug msg=fetch spanID=9460e5b6e64cec91 traceID=b162d3040ddf86d6614e79c66a01a577
time="2022-02-06T17:47:48Z" level=debug msg=fetch spanID=9460e5b6e64cec91 traceID=b162d3040ddf86d6614e79c66a01a577
time="2022-02-06T17:47:48Z" level=debug msg="do request" request.header.accept="application/vnd.docker.image.rootfs.diff.tar.gzip, */*" request.header.user-agent=containerd/1.5.8+unknown request.method=GET spanID=9460e5b6e64cec91 traceID=b162d3040ddf86d6614e79c66a01a577
time="2022-02-06T17:47:48Z" level=debug msg="fetch response received" response.header.accept-ranges=bytes response.header.age=1356 response.header.alt-svc="h3=\":443\"; ma=2592000,h3-29=\":443\"; ma=2592000,h3-Q050=\":443\"; ma=2592000,h3-Q046=\":443\"; ma=2592000,h3-Q043=\":443\"; ma=2592000,quic=\":443\"; ma=2592000; v=\"46,43\"" response.header.cache-control="public, max-age=3600" response.header.content-length=2818413 response.header.content-type=application/octet-stream response.header.date="Sun, 06 Feb 2022 17:25:17 GMT" response.header.etag="\"1d55e7be5a77c4a908ad11bc33ebea1c\"" response.header.expires="Sun, 06 Feb 2022 18:25:17 GMT" response.header.last-modified="Wed, 24 Nov 2021 21:07:06 GMT" response.header.server=UploadServer response.header.x-goog-generation=1637788026431708 response.header.x-goog-hash="crc32c=ZojF+g==" response.header.x-goog-hash.1="md5=HVXnvlp3xKkIrRG8M+vqHA==" response.header.x-goog-metageneration=1 response.header.x-goog-storage-class=STANDARD response.header.x-goog-stored-content-encoding=identity response.header.x-goog-stored-content-length=2818413 response.header.x-guploader-uploadid=ADPycdsebqxiTBJqZ0bv9zBigjFxgQydD2ESZSkKchpE0ILlN9Ibko3C5r4fJTJ4UR9ddp-UBd-2v_4eRpZ8Yo2llW_j4k8WhQ response.status="200 OK" spanID=9460e5b6e64cec91 traceID=b162d3040ddf86d6614e79c66a01a577
...
```

## Setting registry certificates

If you specify registry certificates in the BuildKit configuration, the daemon
copies the files into the container under `/etc/buildkit/certs`. The following
steps show adding a self-signed registry certificate to the BuildKit
configuration.

1. Add the following configuration to `/etc/buildkitd.toml`:

   ```toml
   # /etc/buildkitd.toml
   debug = true
   [registry."myregistry.com"]
     ca=["/etc/certs/myregistry.pem"]
     [[registry."myregistry.com".keypair]]
       key="/etc/certs/myregistry_key.pem"
       cert="/etc/certs/myregistry_cert.pem"
   ```

   This tells the builder to push images to the `myregistry.com` registry using
   the certificates in the specified location (`/etc/certs`).

2. Create a `docker-container` builder that uses this configuration:

   ```console
   $ docker buildx create --use --bootstrap \
     --name mybuilder \
     --driver docker-container \
     --buildkitd-config /etc/buildkitd.toml
   ```

3. Inspect the builder's configuration file (`/etc/buildkit/buildkitd.toml`), it
   shows that the certificate configuration is now configured in the builder.

   ```console
   $ docker exec -it buildx_buildkit_mybuilder0 cat /etc/buildkit/buildkitd.toml
   ```

   ```toml
   debug = true

   [registry]

     [registry."myregistry.com"]
       ca = ["/etc/buildkit/certs/myregistry.com/myregistry.pem"]

       [[registry."myregistry.com".keypair]]
         cert = "/etc/buildkit/certs/myregistry.com/myregistry_cert.pem"
         key = "/etc/buildkit/certs/myregistry.com/myregistry_key.pem"
   ```

4. Verify that the certificates are inside the container:

   ```console
   $ docker exec -it buildx_buildkit_mybuilder0 ls /etc/buildkit/certs/myregistry.com/
   myregistry.pem    myregistry_cert.pem   myregistry_key.pem
   ```

Now you can push to the registry using this builder, and it will authenticate
using the certificates:

```console
$ docker buildx build --push --tag myregistry.com/myimage:latest .
```

## CNI networking

CNI networking for builders can be useful for dealing with network port
contention during concurrent builds. CNI is [not yet](https://github.com/moby/buildkit/issues/28)
available in the default BuildKit image. But you can create your own image that
includes CNI support.

The following Dockerfile example shows a custom BuildKit image with CNI support.
It uses the [CNI config for integration tests](https://github.com/moby/buildkit/blob/master//hack/fixtures/cni.json)
in BuildKit as an example. Feel free to include your own CNI configuration.

```dockerfile
# syntax=docker/dockerfile:1

ARG BUILDKIT_VERSION=v{{% param "buildkit_version" %}}
ARG CNI_VERSION=v1.0.1

FROM --platform=$BUILDPLATFORM alpine AS cni-plugins
RUN apk add --no-cache curl
ARG CNI_VERSION
ARG TARGETOS
ARG TARGETARCH
WORKDIR /opt/cni/bin
RUN curl -Ls https://github.com/containernetworking/plugins/releases/download/$CNI_VERSION/cni-plugins-$TARGETOS-$TARGETARCH-$CNI_VERSION.tgz | tar xzv

FROM moby/buildkit:${BUILDKIT_VERSION}
ARG BUILDKIT_VERSION
RUN apk add --no-cache iptables
COPY --from=cni-plugins /opt/cni/bin /opt/cni/bin
ADD https://raw.githubusercontent.com/moby/buildkit/${BUILDKIT_VERSION}/hack/fixtures/cni.json /etc/buildkit/cni.json
```

Now you can build this image, and create a builder instance from it using
[the `--driver-opt image` option](/reference/cli/docker/buildx/create.md#driver-opt):

```console
$ docker buildx build --tag buildkit-cni:local --load .
$ docker buildx create --use --bootstrap \
  --name mybuilder \
  --driver docker-container \
  --driver-opt "image=buildkit-cni:local" \
  --buildkitd-flags "--oci-worker-net=cni"
```

## Resource limiting

### Max parallelism

You can limit the parallelism of the BuildKit solver, which is particularly useful
for low-powered machines, using a [BuildKit configuration](toml-configuration.md)
while creating a builder with the [`--buildkitd-config` flag](/reference/cli/docker/buildx/create.md#buildkitd-config).

```toml
# /etc/buildkitd.toml
[worker.oci]
  max-parallelism = 4
```

Now you can [create a `docker-container` builder](/manuals/build/builders/drivers/docker-container.md)
that will use this BuildKit configuration to limit parallelism.

```console
$ docker buildx create --use \
  --name mybuilder \
  --driver docker-container \
  --buildkitd-config /etc/buildkitd.toml
```

### TCP connection limit

TCP connections are limited to 4 simultaneous connections per registry for
pulling and pushing images, plus one additional connection dedicated to metadata
requests. This connection limit prevents your build from getting stuck while
pulling images. The dedicated metadata connection helps reduce the overall build
time.

More information: [moby/buildkit#2259](https://github.com/moby/buildkit/pull/2259)

Custom Dockerfile syntax


## Dockerfile frontend

BuildKit supports loading frontends dynamically from container images. To use
an external Dockerfile frontend, the first line of your [Dockerfile](/reference/dockerfile.md)
needs to set the [`syntax` directive](/reference/dockerfile.md#syntax)
pointing to the specific image you want to use:

```dockerfile
# syntax=[remote image reference]
```

For example:

```dockerfile
# syntax=docker/dockerfile:1
# syntax=docker.io/docker/dockerfile:1
# syntax=example.com/user/repo:tag@sha256:abcdef...
```

You can also use the predefined `BUILDKIT_SYNTAX` build argument to set the
frontend image reference on the command line:

```console
$ docker build --build-arg BUILDKIT_SYNTAX=docker/dockerfile:1 .
```

This defines the location of the Dockerfile syntax that is used to build the
Dockerfile. The BuildKit backend allows seamlessly using external
implementations that are distributed as Docker images and execute inside a
container sandbox environment.

Custom Dockerfile implementations allow you to:

- Automatically get bug fixes without updating the Docker daemon
- Make sure all users are using the same implementation to build your Dockerfile
- Use the latest features without updating the Docker daemon
- Try out new features or third-party features before they are integrated in the Docker daemon
- Use [alternative build definitions, or create your own](https://github.com/moby/buildkit#exploring-llb)
- Build your own Dockerfile frontend with custom features

> [!NOTE]
>
> BuildKit ships with a built-in Dockerfile frontend, but it's recommended
> to use an external image to make sure that all users use the same version on
> the builder and to pick up bug fixes automatically without waiting for a new
> version of BuildKit or Docker Engine.

## Official releases

Docker distributes official versions of the images that can be used for building
Dockerfiles under `docker/dockerfile` repository on Docker Hub. There are two
channels where new images are released: `stable` and `labs`.

### Stable channel

The `stable` channel follows [semantic versioning](https://semver.org).
For example:

- `docker/dockerfile:1` - kept updated with the latest `1.x.x` minor _and_ patch
  release.
- `docker/dockerfile:1.2` - kept updated with the latest `1.2.x` patch release,
  and stops receiving updates once version `1.3.0` is released.
- `docker/dockerfile:1.2.1` - immutable: never updated.

We recommend using `docker/dockerfile:1`, which always points to the latest
stable release of the version 1 syntax, and receives both "minor" and "patch"
updates for the version 1 release cycle. BuildKit automatically checks for
updates of the syntax when performing a build, making sure you are using the
most current version.

If a specific version is used, such as `1.2` or `1.2.1`, the Dockerfile needs
to be updated manually to continue receiving bugfixes and new features. Old
versions of the Dockerfile remain compatible with the new versions of the
builder.

### Labs channel

The `labs` channel provides early access to Dockerfile features that are not yet
available in the `stable` channel. `labs` images are released at the same time
as stable releases, and follow the same version pattern, but use the `-labs`
suffix, for example:

- `docker/dockerfile:labs` - latest release on `labs` channel.
- `docker/dockerfile:1-labs` - same as `dockerfile:1`, with experimental
  features enabled.
- `docker/dockerfile:1.2-labs` - same as `dockerfile:1.2`, with experimental
  features enabled.
- `docker/dockerfile:1.2.1-labs` - immutable: never updated. Same as
  `dockerfile:1.2.1`, with experimental features enabled.

Choose a channel that best fits your needs. If you want to benefit from
new features, use the `labs` channel. Images in the `labs` channel contain
all the features in the `stable` channel, plus early access features.
Stable features in the `labs` channel follow [semantic versioning](https://semver.org),
but early access features don't, and newer releases may not be backwards
compatible. Pin the version to avoid having to deal with breaking changes.

## Other resources

For documentation on `labs` features, master builds, and nightly feature
releases, refer to the description in [the BuildKit source repository on GitHub](https://github.com/moby/buildkit/blob/master/README.md).
For a full list of available images, visit the [`docker/dockerfile` repository on Docker Hub](https://hub.docker.com/r/docker/dockerfile),
and the [`docker/dockerfile-upstream` repository on Docker Hub](https://hub.docker.com/r/docker/dockerfile-upstream)
for development builds.

Dockerfile release notes


This page contains information about the new features, improvements, known
issues, and bug fixes in [Dockerfile reference](/reference/dockerfile.md).

For usage, see the [Dockerfile frontend syntax](frontend.md) page.

## 1.18.0

{{< release-date date="2025-09-03" >}}

The full release notes for this release are available
[on GitHub](https://github.com/moby/buildkit/releases/tag/dockerfile%2F1.18.0).

```dockerfile
# syntax=docker/dockerfile:1.18.0
```

* Add support for Git URLs for remote build contexts and `ADD` command now allows new syntax with added query parameters in `?key=value` format for better control over the Git clone procedure. Supported options in this release are `ref`, `tag`, `branch`, `checksum` (alias `commit`), `subdir`, `keep-git-dir` and `submodules`. [moby/buildkit#6172](https://github.com/moby/buildkit/pull/6172) [moby/buildkit#6173](https://github.com/moby/buildkit/pull/6173) 
* Add new check rules `ExposeProtoCasing` and `ExposeInvalidFormat` to improve usage of `EXPOSE` commands. [moby/buildkit#6135](https://github.com/moby/buildkit/pull/6135)
* Fix created time not being set correctly from the base image if named context is used. [moby/buildkit#6096](https://github.com/moby/buildkit/pull/6096)

## 1.17.0

{{< release-date date="2025-06-17" >}}

The full release notes for this release are available
[on GitHub](https://github.com/moby/buildkit/releases/tag/dockerfile%2F1.17.0).

```dockerfile
# syntax=docker/dockerfile:1.17.0
```

* Add `ADD --unpack=bool` to control whether archives from a URL path are unpacked. The default is to detect unpack behavior based on the source path, as it happened in previous versions. [moby/buildkit#5991](https://github.com/moby/buildkit/pull/5991)
* Add support for `ADD --chown` when unpacking archive, similar to when copying regular files. [moby/buildkit#5987](https://github.com/moby/buildkit/pull/5987)

## 1.16.0

{{< release-date date="2025-05-22" >}}

The full release notes for this release are available
[on GitHub](https://github.com/moby/buildkit/releases/tag/dockerfile%2F1.16.0).

```dockerfile
# syntax=docker/dockerfile:1.16.0
```

* `ADD --checksum` support for Git URL. [moby/buildkit#5975](https://github.com/moby/buildkit/pull/5975)
* Allow whitespace in heredocs. [moby/buildkit#5817](https://github.com/moby/buildkit/pull/5817)
* `WORKDIR` now supports `SOURCE_DATE_EPOCH`. [moby/buildkit#5960](https://github.com/moby/buildkit/pull/5960)
* Leave default PATH environment variable set by the base image for WCOW. [moby/buildkit#5895](https://github.com/moby/buildkit/pull/5895)

## 1.15.1

{{< release-date date="2025-03-30" >}}

The full release notes for this release are available
[on GitHub](https://github.com/moby/buildkit/releases/tag/dockerfile%2F1.15.1).

```dockerfile
# syntax=docker/dockerfile:1.15.1
```

* Fix `no scan targets for linux/arm64/v8` when `--attest type=sbom` is used. [moby/buildkit#5941](https://github.com/moby/buildkit/pull/5941)

## 1.15.0

{{< release-date date="2025-04-15" >}}

The full release notes for this release are available
[on GitHub](https://github.com/moby/buildkit/releases/tag/dockerfile%2F1.15.0).

```dockerfile
# syntax=docker/dockerfile:1.15.0
```

- Build error for invalid target now shows suggestions for correct possible names. [moby/buildkit#5851](https://github.com/moby/buildkit/pull/5851)
- Fix SBOM attestation producing error for Windows targets. [moby/buildkit#5837](https://github.com/moby/buildkit/pull/5837)
- Fix recursive `ARG` producing an infinite loop when processing an outline request. [moby/buildkit#5823](https://github.com/moby/buildkit/pull/5823)
- Fix parsing syntax directive from JSON that would fail if the JSON had other datatypes than strings. [moby/buildkit#5815](https://github.com/moby/buildkit/pull/5815)
- Fix platform in image config being in unnormalized form (regression from 1.12). [moby/buildkit#5776](https://github.com/moby/buildkit/pull/5776)
- Fix copying into destination directory when directory is not present with WCOW. [moby/buildkit#5249](https://github.com/moby/buildkit/pull/5249)

## 1.14.1

{{< release-date date="2025-03-05" >}}

The full release notes for this release are available
[on GitHub](https://github.com/moby/buildkit/releases/tag/dockerfile%2F1.14.1).

```dockerfile
# syntax=docker/dockerfile:1.14.1
```

- Normalize platform in image config. [moby/buildkit#5776](https://github.com/moby/buildkit/pull/5776)

## 1.14.0

{{< release-date date="2025-02-19" >}}

The full release notes for this release are available
[on GitHub](https://github.com/moby/buildkit/releases/tag/dockerfile%2F1.14.0).

```dockerfile
# syntax=docker/dockerfile:1.14.0
```

- `COPY --chmod` now allows non-octal values. This feature was previously in the labs channel and is now available in the main release. [moby/buildkit#5734](https://github.com/moby/buildkit/pull/5734)
- Fix handling of OSVersion platform property if one is set by the base image [moby/buildkit#5714](https://github.com/moby/buildkit/pull/5714)
- Fix errors where a named context metadata could be resolved even if it was not reachable by the current build configuration, leading to build errors [moby/buildkit#5688](https://github.com/moby/buildkit/pull/5688)

## 1.14.0 (labs)

{{< release-date date="2025-02-19" >}}

{{% include "dockerfile-labs-channel.md" %}}

The full release notes for this release are available
[on GitHub](https://github.com/moby/buildkit/releases/tag/dockerfile%2F1.14.0-labs).

```dockerfile
# syntax=docker.io/docker/dockerfile-upstream:1.14.0-labs
```

- New `RUN --device=name,[required]` flag lets builds request CDI devices are available to the build step. Requires BuildKit v0.20.0+ [moby/buildkit#4056](https://github.com/moby/buildkit/pull/4056), [moby/buildkit#5738](https://github.com/moby/buildkit/pull/5738)

## 1.13.0

{{< release-date date="2025-01-20" >}}

The full release notes for this release are available
[on GitHub](https://github.com/moby/buildkit/releases/tag/dockerfile%2F1.13.0).

```dockerfile
# syntax=docker/dockerfile:1.13.0
```

- New `TARGETOSVERSION`, `BUILDOSVERSION` builtin build-args are available for Windows builds, and `TARGETPLATFORM` value now also contains `OSVersion` value. [moby/buildkit#5614](https://github.com/moby/buildkit/pull/5614)
- Allow syntax forwarding for external frontends for files starting with a Byte Order Mark (BOM). [moby/buildkit#5645](https://github.com/moby/buildkit/pull/5645)
- Default `PATH` in Windows Containers has been updated with `powershell.exe` directory. [moby/buildkit#5446](https://github.com/moby/buildkit/pull/5446)
- Fix Dockerfile directive parsing to not allow invalid syntax. [moby/buildkit#5646](https://github.com/moby/buildkit/pull/5646)
- Fix case where `ONBUILD` command may have run twice on inherited stage. [moby/buildkit#5593](https://github.com/moby/buildkit/pull/5593)
- Fix possible missing named context replacement for child stages in Dockerfile. [moby/buildkit#5596](https://github.com/moby/buildkit/pull/5596)

## 1.13.0 (labs)

{{< release-date date="2025-01-20" >}}

{{% include "dockerfile-labs-channel.md" %}}

The full release notes for this release are available
[on GitHub](https://github.com/moby/buildkit/releases/tag/dockerfile%2F1.13.0-labs).

```dockerfile
# syntax=docker.io/docker/dockerfile-upstream:1.13.0-labs
```

- Fix support for non-octal values for `COPY --chmod`. [moby/buildkit#5626](https://github.com/moby/buildkit/pull/5626)

## 1.12.0

{{< release-date date="2024-11-27" >}}

The full release notes for this release are available
[on GitHub](https://github.com/moby/buildkit/releases/tag/dockerfile%2F1.12.0).

```dockerfile
# syntax=docker/dockerfile:1.12.0
```

- Fix incorrect description in History line of image configuration with multiple `ARG` instructions. [moby/buildkit#5508]

[moby/buildkit#5508]: https://github.com/moby/buildkit/pull/5508

## 1.11.1

{{< release-date date="2024-11-08" >}}

The full release notes for this release are available
[on GitHub](https://github.com/moby/buildkit/releases/tag/dockerfile%2F1.11.1).

```dockerfile
# syntax=docker/dockerfile:1.11.1
```

- Fix regression when using the `ONBUILD` instruction in stages inherited within the same Dockerfile. [moby/buildkit#5490]

[moby/buildkit#5490]: https://github.com/moby/buildkit/pull/5490

## 1.11.0

{{< release-date date="2024-10-30" >}}

The full release notes for this release are available
[on GitHub](https://github.com/moby/buildkit/releases/tag/dockerfile%2F1.11.0).

```dockerfile
# syntax=docker/dockerfile:1.11.0
```

- The [`ONBUILD` instruction](/reference/dockerfile.md#onbuild) now supports commands that refer to other stages or images with `from`, such as `COPY --from` or `RUN mount=from=...`. [moby/buildkit#5357]
- The [`SecretsUsedInArgOrEnv`](/reference/build-checks/secrets-used-in-arg-or-env.md) build check has been improved to reduce false positives. [moby/buildkit#5208]
- A new [`InvalidDefinitionDescription`](/reference/build-checks/invalid-definition-description.md) build check recommends formatting comments for build arguments and stages descriptions. This is an [experimental check](/manuals/build/checks.md#experimental-checks). [moby/buildkit#5208], [moby/buildkit#5414]
- Multiple fixes for the `ONBUILD` instruction's progress and error handling. [moby/buildkit#5397]
- Improved error reporting for missing flag errors. [moby/buildkit#5369]
- Enhanced progress output for secret values mounted as environment variables. [moby/buildkit#5336]
- Added built-in build argument `TARGETSTAGE` to expose the name of the (final) target stage for the current build. [moby/buildkit#5431]

## 1.11.0 (labs)

{{% include "dockerfile-labs-channel.md" %}}

- `COPY --chmod` now supports non-octal values. [moby/buildkit#5380]

[moby/buildkit#5357]: https://github.com/moby/buildkit/pull/5357
[moby/buildkit#5208]: https://github.com/moby/buildkit/pull/5208
[moby/buildkit#5414]: https://github.com/moby/buildkit/pull/5414
[moby/buildkit#5397]: https://github.com/moby/buildkit/pull/5397
[moby/buildkit#5369]: https://github.com/moby/buildkit/pull/5369
[moby/buildkit#5336]: https://github.com/moby/buildkit/pull/5336
[moby/buildkit#5431]: https://github.com/moby/buildkit/pull/5431
[moby/buildkit#5380]: https://github.com/moby/buildkit/pull/5380

## 1.10.0

{{< release-date date="2024-09-10" >}}

The full release notes for this release are available
[on GitHub](https://github.com/moby/buildkit/releases/tag/dockerfile%2F1.10.0).

```dockerfile
# syntax=docker/dockerfile:1.10.0
```

- [Build secrets](/manuals/build/building/secrets.md#target) can now be mounted as environment variables using the `env=VARIABLE` option. [moby/buildkit#5215]
- The [`# check` directive](/reference/dockerfile.md#check) now allows new experimental attribute for enabling experimental validation rules like `CopyIgnoredFile`. [moby/buildkit#5213]
- Improve validation of unsupported modifiers for variable substitution. [moby/buildkit#5146]
- `ADD` and `COPY` instructions now support variable interpolation for build arguments for the `--chmod` option values. [moby/buildkit#5151]
- Improve validation of the `--chmod` option for `COPY` and `ADD` instructions. [moby/buildkit#5148]
- Fix missing completions for size and destination attributes on mounts. [moby/buildkit#5245]
- OCI annotations are now set to the Dockerfile frontend release image. [moby/buildkit#5197]

[moby/buildkit#5215]: https://github.com/moby/buildkit/pull/5215
[moby/buildkit#5213]: https://github.com/moby/buildkit/pull/5213
[moby/buildkit#5146]: https://github.com/moby/buildkit/pull/5146
[moby/buildkit#5151]: https://github.com/moby/buildkit/pull/5151
[moby/buildkit#5148]: https://github.com/moby/buildkit/pull/5148
[moby/buildkit#5245]: https://github.com/moby/buildkit/pull/5245
[moby/buildkit#5197]: https://github.com/moby/buildkit/pull/5197

## 1.9.0

{{< release-date date="2024-07-11" >}}

The full release notes for this release are available
[on GitHub](https://github.com/moby/buildkit/releases/tag/dockerfile%2F1.9.0).

```dockerfile
# syntax=docker/dockerfile:1.9.0
```

- Add new validation rules:
  - `SecretsUsedInArgOrEnv`
  - `InvalidDefaultArgInFrom`
  - `RedundantTargetPlatform`
  - `CopyIgnoredFile` (experimental)
  - `FromPlatformFlagConstDisallowed`
- Many performance improvements for working with big Dockerfiles. [moby/buildkit#5067](https://github.com/moby/buildkit/pull/5067/), [moby/buildkit#5029](https://github.com/moby/buildkit/pull/5029/)
- Fix possible panic when building Dockerfile without defined stages. [moby/buildkit#5150](https://github.com/moby/buildkit/pull/5150/)
- Fix incorrect JSON parsing that could cause some incorrect JSON values to pass without producing an error. [moby/buildkit#5107](https://github.com/moby/buildkit/pull/5107/)
- Fix a regression where `COPY --link` with a destination path of `.` could fail. [moby/buildkit#5080](https://github.com/moby/buildkit/pull/5080/)
- Fix validation of `ADD --checksum` when used with a Git URL. [moby/buildkit#5085](https://github.com/moby/buildkit/pull/5085/)

## 1.8.1

{{< release-date date="2024-06-18" >}}

The full release notes for this release are available
[on GitHub](https://github.com/moby/buildkit/releases/tag/dockerfile%2F1.8.1).

```dockerfile
# syntax=docker/dockerfile:1.8.1
```

### Bug fixes and enhancements

- Fix handling of empty strings on variable expansion. [moby/buildkit#5052](https://github.com/moby/buildkit/pull/5052/)
- Improve formatting of build warnings. [moby/buildkit#5037](https://github.com/moby/buildkit/pull/5037/), [moby/buildkit#5045](https://github.com/moby/buildkit/pull/5045/), [moby/buildkit#5046](https://github.com/moby/buildkit/pull/5046/)
- Fix possible invalid output for `UndeclaredVariable` warning for multi-stage builds. [moby/buildkit#5048](https://github.com/moby/buildkit/pull/5048/)

## 1.8.0

{{< release-date date="2024-06-11" >}}

The full release notes for this release are available
[on GitHub](https://github.com/moby/buildkit/releases/tag/dockerfile%2F1.8.0).

```dockerfile
# syntax=docker/dockerfile:1.8.0
```

- Many new validation rules have been added to verify that your Dockerfile is using best practices. These rules are validated during build and new `check` frontend method can be used to only trigger validation without completing the whole build.
- New directive `#check` and build argument `BUILDKIT_DOCKERFILE_CHECK` lets you control the behavior or build checks. [moby/buildkit#4962](https://github.com/moby/buildkit/pull/4962/)
- Using a single-platform base image that does not match your expected platform is now validated. [moby/buildkit#4924](https://github.com/moby/buildkit/pull/4924/)
- Errors from the expansion of `ARG` definitions in global scope are now handled properly. [moby/buildkit#4856](https://github.com/moby/buildkit/pull/4856/)
- Expansion of the default value of `ARG` now only happens if it is not overwritten by the user. Previously, expansion was completed and value was later ignored, which could result in an unexpected expansion error. [moby/buildkit#4856](https://github.com/moby/buildkit/pull/4856/)
- Performance of parsing huge Dockerfiles with many stages has been improved. [moby/buildkit#4970](https://github.com/moby/buildkit/pull/4970/)
- Fix some Windows path handling consistency errors. [moby/buildkit#4825](https://github.com/moby/buildkit/pull/4825/)

## 1.7.0

{{< release-date date="2024-03-06" >}}

### Stable

```dockerfile
# syntax=docker/dockerfile:1.7
```

- Variable expansion now allows string substitutions and trimming.
  [moby/buildkit#4427](https://github.com/moby/buildkit/pull/4427),
  [moby/buildkit#4287](https://github.com/moby/buildkit/pull/4287)
- Named contexts with local sources now correctly transfer only the files used in the Dockerfile instead of the full source directory.
  [moby/buildkit#4161](https://github.com/moby/buildkit/pull/4161)
- Dockerfile now better validates the order of stages and returns nice errors with stack traces if stages are in incorrect order.
  [moby/buildkit#4568](https://github.com/moby/buildkit/pull/4568),
  [moby/buildkit#4567](https://github.com/moby/buildkit/pull/4567)
- History commit messages now contain flags used with `COPY` and `ADD`.
  [moby/buildkit#4597](https://github.com/moby/buildkit/pull/4597)
- Progress messages for `ADD` commands from Git and HTTP sources have been improved.
  [moby/buildkit#4408](https://github.com/moby/buildkit/pull/4408)

### Labs

```dockerfile
# syntax=docker/dockerfile:1.7-labs
```

- New `--parents` flag has been added to `COPY` for copying files while keeping the parent directory structure.
  [moby/buildkit#4598](https://github.com/moby/buildkit/pull/4598),
  [moby/buildkit#3001](https://github.com/moby/buildkit/pull/3001),
  [moby/buildkit#4720](https://github.com/moby/buildkit/pull/4720),
  [moby/buildkit#4728](https://github.com/moby/buildkit/pull/4728),
  [docs](/reference/dockerfile.md#copy---parents)
- New `--exclude` flag can be used in `COPY` and `ADD` commands to apply filter to copied files.
  [moby/buildkit#4561](https://github.com/moby/buildkit/pull/4561),
  [docs](/reference/dockerfile.md#copy---exclude)

## 1.6.0

{{< release-date date="2023-06-13" >}}

### New

- Add `--start-interval` flag to the
  [`HEALTHCHECK` instruction](/reference/dockerfile.md#healthcheck).

The following features have graduated from the labs channel to stable:

- The `ADD` instruction can now [import files directly from Git URLs](/reference/dockerfile.md#adding-a-git-repository-add-git-ref-dir)
- The `ADD` instruction now supports [`--checksum` flag](/reference/dockerfile.md#verifying-a-remote-file-checksum-add---checksumchecksum-http-src-dest)
  to validate the contents of the remote URL contents

### Bug fixes and enhancements

- Variable substitution now supports additional POSIX compatible variants without `:`.
  [moby/buildkit#3611](https://github.com/moby/buildkit/pull/3611)
- Exported Windows images now contain OSVersion and OSFeatures values from base image.
  [moby/buildkit#3619](https://github.com/moby/buildkit/pull/3619)
- Changed the permissions for Heredocs to 0644.
  [moby/buildkit#3992](https://github.com/moby/buildkit/pull/3992)

## 1.5.2

{{< release-date date="2023-02-14" >}}

### Bug fixes and enhancements

- Fix building from Git reference that is missing branch name but contains a
  subdir
- 386 platform image is now included in the release

## 1.5.1

{{< release-date date="2023-01-18" >}}

### Bug fixes and enhancements

- Fix possible panic when warning conditions appear in multi-platform builds

## 1.5.0 (labs)

{{< release-date date="2023-01-10" >}}

{{% include "dockerfile-labs-channel.md" %}}

### New

- `ADD` command now supports [`--checksum` flag](/reference/dockerfile.md#verifying-a-remote-file-checksum-add---checksumchecksum-http-src-dest)
  to validate the contents of the remote URL contents

## 1.5.0

{{< release-date date="2023-01-10" >}}

### New

- `ADD` command can now [import files directly from Git URLs](/reference/dockerfile.md#adding-a-git-repository-add-git-ref-dir)

### Bug fixes and enhancements

- Named contexts now support `oci-layout://` protocol for including images from
  local OCI layout structure
- Dockerfile now supports secondary requests for listing all build targets or
  printing outline of accepted parameters for a specific build target
- Dockerfile `#syntax` directive that redirects to an external frontend image
  now allows the directive to be also set with `//` comments or JSON. The file
  may also contain a shebang header
- Named context can now be initialized with an empty scratch image
- Named contexts can now be initialized with an SSH Git URL
- Fix handling of `ONBUILD` when importing Schema1 images

## 1.4.3

{{< release-date date="2022-08-23" >}}

### Bug fixes and enhancements

- Fix creation timestamp not getting reset when building image from
  `docker-image://` named context
- Fix passing `--platform` flag of `FROM` command when loading
  `docker-image://` named context

## 1.4.2

{{< release-date date="2022-05-06" >}}

### Bug fixes and enhancements

- Fix loading certain environment variables from an image passed with built
  context

## 1.4.1

{{< release-date date="2022-04-08" >}}

### Bug fixes and enhancements

- Fix named context resolution for cross-compilation cases from input when input
  is built for a different platform

## 1.4.0

{{< release-date date="2022-03-09" >}}

### New

- [`COPY --link` and `ADD --link`](/reference/dockerfile.md#copy---link)
  allow copying files with increased cache efficiency and rebase images without
  requiring them to be rebuilt. `--link` copies files to a separate layer and
  then uses new LLB MergeOp implementation to chain independent layers together
- [Heredocs](/reference/dockerfile.md#here-documents) support have
  been promoted from labs channel to stable. This feature allows writing
  multiline inline scripts and files
- Additional [named build contexts](/reference/cli/docker/buildx/build.md#build-context)
  can be passed to build to add or overwrite a stage or an image inside the
  build. A source for the context can be a local source, image, Git, or HTTP URL
- [`BUILDKIT_SANDBOX_HOSTNAME` build-arg](/reference/dockerfile.md#buildkit-built-in-build-args)
  can be used to set the default hostname for the `RUN` steps

### Bug fixes and enhancements

- When using a cross-compilation stage, the target platform for a step is now
  seen on progress output
- Fix some cases where Heredocs incorrectly removed quotes from content

## 1.3.1

{{< release-date date="2021-10-04" >}}

### Bug fixes and enhancements

- Fix parsing "required" mount key without a value

## 1.3.0 (labs)

{{< release-date date="2021-07-16" >}}

{{% include "dockerfile-labs-channel.md" %}}

### New

- `RUN` and `COPY` commands now support [Here-document syntax](/reference/dockerfile.md#here-documents)
  allowing writing multiline inline scripts and files

## 1.3.0

{{< release-date date="2021-07-16" >}}

### New

- `RUN` command allows [`--network` flag](/reference/dockerfile.md#run---network)
  for requesting a specific type of network conditions. `--network=host`
  requires allowing `network.host` entitlement. This feature was previously
  only available on labs channel

### Bug fixes and enhancements

- `ADD` command with a remote URL input now correctly handles the `--chmod` flag
- Values for [`RUN --mount` flag](/reference/dockerfile.md#run---mount)
  now support variable expansion, except for the `from` field
- Allow [`BUILDKIT_MULTI_PLATFORM` build arg](/reference/dockerfile.md#buildkit-built-in-build-args)
  to force always creating multi-platform image, even if only contains single
  platform

## 1.2.1 (labs)

{{< release-date date="2020-12-12" >}}

{{% include "dockerfile-labs-channel.md" %}}

### Bug fixes and enhancements

- `RUN` command allows [`--network` flag](/reference/dockerfile.md#run---network)
  for requesting a specific type of network conditions. `--network=host`
  requires allowing `network.host` entitlement

## 1.2.1

{{< release-date date="2020-12-12" >}}

### Bug fixes and enhancements

- Revert "Ensure ENTRYPOINT command has at least one argument"
- Optimize processing `COPY` calls on multi-platform cross-compilation builds

## 1.2.0 (labs)

{{< release-date date="2020-12-03" >}}

{{% include "dockerfile-labs-channel.md" %}}

### Bug fixes and enhancements

- Experimental channel has been renamed to _labs_

## 1.2.0

{{< release-date date="2020-12-03" >}}

### New

- [`RUN --mount` syntax](/reference/dockerfile.md#run---mount) for
  creating secret, ssh, bind, and cache mounts have been moved to mainline
  channel
- [`ARG` command](/reference/dockerfile.md#arg) now supports defining
  multiple build args on the same line similarly to `ENV`

### Bug fixes and enhancements

- Metadata load errors are now handled as fatal to avoid incorrect build results
- Allow lowercase Dockerfile name
- `--chown` flag in `ADD` now allows parameter expansion
- `ENTRYPOINT` requires at least one argument to avoid creating broken images

## 1.1.7

{{< release-date date="2020-04-18" >}}

### Bug fixes and enhancements

- Forward `FrontendInputs` to the gateway

## 1.1.2 (labs)

{{< release-date date="2019-07-31" >}}

{{% include "dockerfile-labs-channel.md" %}}

### Bug fixes and enhancements

- Allow setting security mode for a process with `RUN --security=sandbox|insecure`
- Allow setting uid/gid for [cache mounts](/reference/dockerfile.md#run---mounttypecache)
- Avoid requesting internally linked paths to be pulled to build context
- Ensure missing cache IDs default to target paths
- Allow setting namespace for cache mounts with [`BUILDKIT_CACHE_MOUNT_NS` build arg](/reference/dockerfile.md#buildkit-built-in-build-args)

## 1.1.2

{{< release-date date="2019-07-31" >}}

### Bug fixes and enhancements

- Fix workdir creation with correct user and don't reset custom ownership
- Fix handling empty build args also used as `ENV`
- Detect circular dependencies

## 1.1.0

{{< release-date date="2019-04-27" >}}

### New

- `ADD/COPY` commands now support implementation based on `llb.FileOp` and do
  not require helper image if builtin file operations support is available
- `--chown` flag for `COPY` command now supports variable expansion

### Bug fixes and enhancements

- To find the files ignored from the build context Dockerfile frontend will
  first look for a file `<path/to/Dockerfile>.dockerignore` and if it is not
  found `.dockerignore` file will be looked up from the root of the build
  context. This allows projects with multiple Dockerfiles to use different
  `.dockerignore` definitions
