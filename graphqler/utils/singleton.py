def singleton(myClass):
    instances = {}

    def getInstance(*args, **kwargs):
        if myClass not in instances:
            instances[myClass] = myClass(*args, **kwargs)
        return instances[myClass]

    # Expose the original class so callers can create fresh non-singleton instances
    # when needed (e.g. per-chain ObjectsBucket in the fuzzer):
    #   fresh_bucket = ObjectsBucket.__wrapped__(api)
    setattr(getInstance, "__wrapped__", myClass)

    return getInstance
