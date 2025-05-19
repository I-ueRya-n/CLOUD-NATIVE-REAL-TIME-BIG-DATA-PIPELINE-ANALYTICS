## Cache Testing

To test the cache, create a test function (run these commands from the root directory).
```bash
fission fn create --spec --name elastic-cache-test \
    --pkg elastic-cache \
    --env go \
    --configmap shared-data \
    --entrypoint ItemHandler

fission route create --spec --name elastic-cache-test \
  --url /cache-test/index/{index}/field/{field} \
  --method POST \
  --function elastic-cache-test
```

Port forward to fission router.
```bash
kubectl port-forward service/router -n fission 9090:80
```

Run tests (from the `tests/cache` directory).
```bash
cd tests/cache
go test
```
