# fast-dotenv-rs 0.1.1

`0.1.1` is the first formal release of the complete `python-dotenv==1.2.2`
replacement. It corrects the `0.1.0` distribution contract: a plain
`pip install fast-dotenv-rs==0.1.1` now installs Click and provides the working
`dotenv` console script and `python -m dotenv` entry point without requiring an
extra.

The release uses the same fail-closed pipeline: five native abi3 wheels and one
sdist are built and audited as one immutable artifact set, each advertised
platform reinstalls the base package from public PyPI and reruns the complete
pinned upstream suite, and the formal GitHub Release is created last with
checksums.

```bash
python -m pip install "fast-dotenv-rs==0.1.1"
dotenv --version
```
