# Troubleshooting lab

Five ways a Kubernetes deployment commonly breaks, each as a manifest you can
apply next to the running ClinicCare release. For each one: the symptom, how to
find the cause with `kubectl`, and the fix.

```bash
troubleshooting/run-scenario.sh 3        # apply scenario 3, wait 45 s, run the diagnosis commands
troubleshooting/run-scenario.sh cleanup  # delete everything labelled lab=troubleshooting
```

The script substitutes the image of the running `cliniccare-backend` Deployment
for `IMAGE` in scenarios 3 and 4, so the broken pods use the real application
image. Only the scenario's own configuration is wrong. Every scenario is
labelled `lab=troubleshooting` and never touches the real release.

A general order that finds most problems quickly:

1. `kubectl get pods`: the STATUS and READY columns name the failure class.
2. `kubectl describe pod <pod>`: the **Events** at the bottom say what Kubernetes tried and what failed.
3. `kubectl logs <pod>` (add `--previous` after a restart): what the application itself said.
4. `kubectl get events --sort-by=.lastTimestamp`: for controllers that never managed to create a pod.

| # | Scenario | What you see | Where the cause shows up |
|---|----------|--------------|--------------------------|
| 1 | Image tag doesn't exist | `ErrImagePull`, then `ImagePullBackOff` | `describe pod`, Events |
| 2 | Service selector matches no pods | Service exists; every request fails | EndpointSlice is empty |
| 3 | Wrong database host | `Running` but `0/1` READY | `describe pod` (readiness 503), logs |
| 4 | Typo in the start command | `CrashLoopBackOff`, restarts climbing | `logs --previous` |
| 5 | Pod would run as root | Deployment `0/1`, **no pods at all** | ReplicaSet `FailedCreate` event |

---

## 1. ImagePullBackOff: the image tag doesn't exist

[`01-image-pull-backoff.yaml`](01-image-pull-backoff.yaml) asks for
`ghcr.io/bhuvanesh66/cliniccare-backend:does-not-exist`.

**Symptom.** The pod never starts. STATUS alternates between `ErrImagePull` and
`ImagePullBackOff`, and the kubelet waits longer between each retry.

**Diagnose.**

```bash
kubectl -n cliniccare get pods -l app=broken-image
kubectl -n cliniccare describe pod -l app=broken-image   # Events: Failed to pull image ... not found
```

The Events show the exact image reference and the registry's answer. *not found*
means a wrong name or tag. *unauthorized* or *denied* means a private image with
no `imagePullSecrets`.

**Fix.** Deploy a tag that exists. The pipeline pushes every image as
`cliniccare-<component>:<commit SHA>` and deploys that exact SHA, so this can
only happen if someone edits the tag by hand.

## 2. Service with no endpoints: the selector matches nothing

[`02-service-no-endpoints.yaml`](02-service-no-endpoints.yaml) selects
`app.kubernetes.io/component: api`, but the API pods are labelled `backend`.

**Symptom.** The Service exists and has a ClusterIP, so the configuration looks
right. But every connection to it is refused or times out, and an Ingress in
front of it returns 503.

**Diagnose.**

```bash
kubectl -n cliniccare get endpointslices -l kubernetes.io/service-name=broken-service   # no endpoints
kubectl -n cliniccare get svc broken-service -o jsonpath='{.spec.selector}'
kubectl -n cliniccare get pods -l app.kubernetes.io/name=cliniccare --show-labels
```

Compare the Service's selector with the pods' labels. Every key in the selector
must match exactly.

**Fix.** Correct the selector (`app.kubernetes.io/component: backend`). In the
Helm chart, the Service and the Deployment selectors come from the same
`cliniccare.selectorLabels` helper, so they can't drift apart.

## 3. Readiness failure: Running, but never Ready

[`03-readiness-failure.yaml`](03-readiness-failure.yaml) points
`DATABASE_URL` at `cliniccare-postgress`, a Service that doesn't exist.

**Symptom.** The pod is `Running` with `0/1` READY and no restarts. Kubernetes
sends it no traffic.

**Diagnose.**

```bash
kubectl -n cliniccare describe pod -l app=broken-readiness   # Readiness probe failed: HTTP probe failed with statuscode: 503
kubectl -n cliniccare logs deploy/broken-readiness           # "GET /ready HTTP/1.1" 503, "GET /health HTTP/1.1" 200
```

ClinicCare separates the two probes on purpose:

- `/health` (liveness) only says the process is alive, so it still answers 200.
  Restarting the pod wouldn't fix a bad database address.
- `/ready` (readiness) runs a query against the database. It returns 503 until
  the database is reachable and migrated, so the pod stays out of the Service.

The 503 on `/ready` alongside a 200 on `/health` points at a dependency. The
next thing to check is the `DATABASE_URL`.

**Fix.** Use the real Service name (`cliniccare-postgres`). The chart builds
`DATABASE_URL` into a Secret from the release name, so it can't be misspelled.

## 4. CrashLoopBackOff: the process exits on start

[`04-crashloop.yaml`](04-crashloop.yaml) starts `uvicorn app.mian:app` instead
of `app.main:app`.

**Symptom.** STATUS is `CrashLoopBackOff` and RESTARTS keeps rising. The wait
before each restart doubles, up to 5 minutes.

**Diagnose.**

```bash
kubectl -n cliniccare get pods -l app=broken-crashloop
kubectl -n cliniccare logs deploy/broken-crashloop --previous   # Error loading ASGI app. Could not import module "app.mian".
kubectl -n cliniccare describe pod -l app=broken-crashloop      # Last State: Terminated, Reason: Error, Exit Code: 1
```

`--previous` matters here. The current container may have just restarted and
have no output yet. The crashed one holds the error.

**Fix.** Correct the command. Exit code 1 with an import error is a code or
configuration problem. Exit code 137 with `OOMKilled` would mean the memory
limit is too low instead.

## 5. Pod Security violation: the Deployment creates no pods

[`05-pod-security-violation.yaml`](05-pod-security-violation.yaml) runs busybox
as root (`runAsUser: 0`, `privileged: true`). The `cliniccare` namespace
enforces the **restricted** Pod Security Standard
([`k8s/namespace.yaml`](../k8s/namespace.yaml)).

**Symptom.**

- `kubectl apply` prints `Warning: would violate PodSecurity "restricted:latest"`,
  but the Deployment is still created.
- The Deployment then stays at `0/1`, and `kubectl get pods` shows nothing at all.
  There are no failing pods to describe.

**Diagnose.**

```bash
kubectl -n cliniccare get deploy broken-pod-security          # READY 0/1
kubectl -n cliniccare get events --field-selector reason=FailedCreate
# replicaset/broken-pod-security-...: pods "..." is forbidden: violates PodSecurity "restricted:latest": privileged ...
```

When no pod exists, the error is on the controller one level up. The ReplicaSet
tried to create the pod and the admission controller rejected it.

**Fix.** Run as a non-root user and drop privileges, as every ClinicCare
workload does:

- `runAsNonRoot: true`, plus a numeric `runAsUser`.
- `allowPrivilegeEscalation: false`.
- `capabilities.drop: [ALL]`.
- `seccompProfile: RuntimeDefault`.

The application images already run as uid 10001 (API) and 101 (nginx).
