from grapheneapi.grapheneapi import GrapheneAPI
from bitsharesbase.operations import getOperationNameForId
from bitshares.market import Market
from bitshares import BitShares
import math
import config

if __name__ == "__main__":
    graphene = GrapheneAPI(config.wallet_host, config.wallet_port)
    bts = BitShares(config.witness_url)

    # Get current fees
    core_asset = graphene.get_asset("1.3.0")
    committee_account = graphene.get_account("committee-account")
    proposals = bts.rpc.get_proposed_transactions(committee_account["id"])

    # Get ticker/current price
    market = Market(config.market)
    ticker = market.ticker()
    core_exchange_rate = float(ticker["core_exchange_rate"])
    settlement_price = float(ticker["quoteSettlement_price"])

    for proposal in proposals:
        print("Proposal: %s" % proposal["id"])

        prop_op = proposal["proposed_transaction"]["operations"]

        if len(prop_op) > 1:
            print(" - [Warning] This proposal has more than 1 operation")

        for op in prop_op:

            if op[0] == 31:

                fees = op[1]["new_parameters"]["current_fees"]["parameters"]
                scale = int(op[1]["new_parameters"]["current_fees"]["scale"]) / 1e4

                fee_named = {}
                for f in fees:
                    opName = getOperationNameForId(f[0])
                    fee_named[opName] = f[1].copy()
                    for o in f[1]:
                        if opName in config.native_fees:
                            if config.force_integer_core_fee:
                                fee_named[opName][o] = (
                                    int(int(f[1][o]) / 10 ** core_asset["precision"])
                                    * scale
                                    / settlement_price
                                )
                            else:
                                fee_named[opName][o] = (
                                    int(f[1][o])
                                    / 10 ** core_asset["precision"]
                                    * scale
                                    / settlement_price
                                )

                            core_fee_ist = (
                                int(f[1][o]) / 10 ** core_asset["precision"] * scale
                            )
                            core_fee_soll = (
                                config.native_fees[opName][o] * settlement_price / scale
                            )

                            if config.native_fees[opName][o] != 0.0:
                                scalingfactor = (
                                    (
                                        config.native_fees[opName][o]
                                        / fee_named[opName][o]
                                    )
                                    if fee_named[opName][o]
                                    else 999
                                )
                                if (
                                    math.fabs(1 - scalingfactor)
                                    > config.tolerance_percentage / 100
                                ):
                                    print(
                                        "%23s price for %41s differs by %8.3fx (proposal: %9.4f USD (%12.4f BTS) / target: %9.4f USD (%12.1f BTS))"
                                        % (
                                            o,
                                            opName,
                                            scalingfactor,
                                            fee_named[opName][o],
                                            core_fee_ist,
                                            config.native_fees[opName][o],
                                            core_fee_soll,
                                        )
                                    )
                        else:
                            print(
                                " - [Warning] The parameter %s in operation %s is not defined in your set of native fees!"
                                % (o, opName)
                            )
            else:
                print(
                    " - [Warning] Another operation is part of this proposal: %s"
                    % getOperationNameForId(op[0])
                )
