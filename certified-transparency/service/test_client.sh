#!/usr/bin/env bash

export PATH=/home/markus/go/go1.22.2/bin:$PATH

set -eux

go run ./cmd/client show
go run ./cmd/client preregister go.mod
go run ./cmd/client register go.mod

list=( data-client/sot/*.sot )
sot="${list[-1]}"
list=( data-client/proof/*.proof )
proof="${list[-1]}"
echo "sot = $sot"
echo "proof = $proof"

go run ./cmd/client verify "$sot"
go run ./cmd/client verify "$proof"

index=$(go run ./cmd/client register --data-private "FLAG1" --data-public "FLAG2" go.mod 2>&1 | grep -oP 'log position: \K[0-9]+')
echo "Claimed index: $index"

go run ./cmd/client claim "$sot" "$index"
go run ./cmd/client claim "$proof" "$index"
echo "DONE"
