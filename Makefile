.PHONY: proto clean

# Generate gRPC code
proto:
	mkdir -p proto
	python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. proto/chord.proto

clean:
	rm -rf proto/*.py