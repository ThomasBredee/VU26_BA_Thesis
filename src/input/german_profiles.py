import simbench as sb

def build_pD_from_simbench(net, B, T, S_base_kVA, verbose=False):
    """
    Build active demand profile pD[(bus,t)] directly
    from SimBench standard load profiles.

    Returns:
        pD[(bus,t)] in p.u.
    """


    # -----------------------------------
    # Get SimBench absolute profiles
    # -----------------------------------
    profiles = sb.get_absolute_values(
        net,
        profiles_instead_of_study_cases=True
    )

    # active power load profiles (MW)
    load_profiles = profiles[("load", "p_mw")]

    pD = {}

    # -----------------------------------
    # Build per-bus demand
    # -----------------------------------
    for bus in B:

        # all load elements connected to this bus
        load_ids = net.load[
            net.load.bus == bus
        ].index.tolist()

        # no load at this bus
        if len(load_ids) == 0:
            for t in T:
                pD[(bus, t)] = 0.0
            continue

        # Sum all loads at this bus
        # Result: time series in MW
        bus_profile_mw = load_profiles[
            load_ids
        ].sum(axis=1)

        # Convert:
        # MW -> kW -> p.u.
        bus_profile_pu = (
            bus_profile_mw * 1000
            / S_base_kVA
        )

        # Save into model dictionary
        for t in T:
            pD[(bus, t)] = bus_profile_pu.iloc[t]

    # -----------------------------------
    # Optional print check
    # -----------------------------------
    if verbose:
        print("\n=== Peak demand per bus ===")
        print(f"{'Bus':>5} {'Peak [p.u.]':>12}")

        peak_per_bus = {}

        for bus in B:
            peak = max(
                pD[(bus, t)]
                for t in T
            )
            peak_per_bus[bus] = peak

        for bus, peak in sorted(
            peak_per_bus.items(),
            key=lambda x: x[1],
            reverse=True
        ):
            print(
                f"{bus:>5} "
                f"{peak:>12.4f}"
            )

    return pD

def build_qD_from_simbench(net, B, T, S_base_kVA, verbose=False):
    """
    Build reactive demand profile qD[(bus,t)] from SimBench.

    Returns:
        qD[(bus,t)] in p.u.
    """

    # -----------------------------------
    # Get SimBench profiles
    # -----------------------------------
    profiles = sb.get_absolute_values(
        net,
        profiles_instead_of_study_cases=True
    )

    # Reactive load profiles [MVAr]
    q_profiles = profiles[("load", "q_mvar")]

    qD = {}

    # -----------------------------------
    # Build bus-level reactive demand
    # -----------------------------------
    for bus in B:

        # all load elements connected to this bus
        load_ids = net.load[
            net.load.bus == bus
        ].index.tolist()

        if len(load_ids) == 0:
            for t in T:
                qD[(bus, t)] = 0.0
            continue

        # Sum all loads connected to this bus
        # Result: MVAr time series
        bus_q_profile_mvar = q_profiles[
            load_ids
        ].sum(axis=1)

        # Convert MVAr -> kVAr -> p.u.
        bus_q_profile_pu = (
            bus_q_profile_mvar * 1000
            / S_base_kVA
        )

        # Store into qD dictionary
        for t_idx, t in enumerate(T):
            qD[(bus, t)] = (
                bus_q_profile_pu.iloc[t_idx]
            )

    # -----------------------------------
    # Optional check
    # -----------------------------------
    if verbose:
        print("\nReactive demand qD created from SimBench.")
        print("Sample values:")

        for bus in list(B)[:5]:
            vals = [
                qD[(bus, t)]
                for t in list(T)[:3]
            ]
            print(
                f"Bus {bus:>3}: "
                f"{[round(v,6) for v in vals]}"
            )

    return qD