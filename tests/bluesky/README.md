## Bluesky Testing

Port forward to fission router.
```bash
kubectl port-forward service/router -n fission 9090:80
```

Run tests
```bash
cd tests/bluesky
go test
```
