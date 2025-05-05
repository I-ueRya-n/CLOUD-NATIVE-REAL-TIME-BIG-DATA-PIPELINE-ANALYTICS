FROM golang:1.23-alpine AS builder

ENV CGO_ENABLED=0 \
    GOOS=linux \
    GOARCH=amd64

WORKDIR /build
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN go build -o /app .

FROM alpine:3.17 AS final
COPY --from=builder /app /bin/app

CMD ["bin/app"]
