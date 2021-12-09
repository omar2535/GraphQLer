# Fengine

The fuzzer-engine. This is the bread-and-butter of grpahql fuzzing.

## Making your own fuzzer

To create a fuzzer, follow the example of `ddos_fuzzer.py`. In essence, there are a few steps required:

1. Extend the base `Fuzzer class`
2. Parse the params
3. Parse the body
4. Write tests
5. Commit!

## Notes about output types

There are defaults in `fuzzer.py` that can be overrided with user-defined payloads. These are:

- `fuzzables`: Defined by a dictionary so that when seeing these in parameter parsing for a `graphqlRequest` object, the fuzzer can use this defined fuzzable instead. See `fuzzer.get_fuzzable()` for more details
- `datatypes`: This is the global object to be used to check for datatypes for every fuzzer
