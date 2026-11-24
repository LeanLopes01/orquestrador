#!/usr/bin/env bash
set -euo pipefail
sudo jarvis-deploy /tmp/jarvis-backend-20261021T005253Z-companion.tar.gz a57034194077b81188ae39ea1f3ebdf0685e254515afb98ded6a09b479c9caef
sudo jarvis-control master 931e18105a3641f98948555713e79641 --off
sudo jarvis-control work 931e18105a3641f98948555713e79641
sudo jarvis-control work 79652afcd37f48148e028142965d4caf
sudo jarvis-control devices
echo "PUBLICACAO CONCLUIDA: S23 FE companion, Motorola preservado."
