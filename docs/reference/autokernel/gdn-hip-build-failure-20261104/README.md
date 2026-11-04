# GDN HIP build failure and repair

The original build failed on malformed staged C++ at the BF16 test registration. Raw logs, CMake cache and patches are gzip-compressed to preserve their exact bytes; RAW-SHA256SUMS binds the decompressed bytes. Decompress the successor patch before checking its original packet-file manifest. The successor snapshot records compile qualification only; full build and native oracle results remain outstanding.
