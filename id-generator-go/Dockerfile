# Build stage
FROM golang:1.24.0-alpine3.21

WORKDIR /app

# Copy the source code and build the binary
COPY . .

# Download dependencies
RUN go mod download


# Build
RUN CGO_ENABLED=0 GOOS=linux go build -o /id-generator

EXPOSE 8000

CMD ["/id-generator"]
