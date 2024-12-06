#!/usr/bin/env bash

set +e

# use the same script to release the demo service

find . -name '*.md' -exec sed -i 's|https://gitlab.saarsec.rocks/saarctf/example_service/-/blob|https://github.com/MarkusBauer/saarctf-example-service/blob|' {} \;
find . -name '*.md' -exec sed -i 's|https://gitlab.saarsec.rocks/saarctf/example_service|https://github.com/MarkusBauer/saarctf-example-service|' {} \;
find . -name '*.md' -exec sed -i 's|https://gitlab.saarsec.rocks/saarctf/gamelib/-/blob|https://github.com/MarkusBauer/saarctf-gamelib/blob|' {} \;
rm prepare-release.sh
echo "DONE"
