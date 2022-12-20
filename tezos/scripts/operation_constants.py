# The maximum number of single operations/transactions in one bulk operation to not exceed the max_operation_data_length=32768 if high transfer amount
MAX_OPS_BULK = 500
# Amount of blocks an unconfirmed transaction stays in the mempool
OPS_TTL = 5
# Gas limit per operation
OPS_GAS_LIMIT = 1420
# Storage limit for bulk operation
OPS_STORAGE_LIMIT_BULK = 357
# Storage limit per operation
OPS_STORAGE_LIMIT = 257
# Total supply of tez that can be written to the activation protocol / parameters file under the extreme cases of 1 second block delay and all 126 bakers
MAX_BOOTSTRAP_SUPPLY_TEZ = 60000000  # 68,040,000
# Default amount of tez per baker account
AMOUNT_OF_TEZ_B_DEFAULT = 50000
# Fees for standard transfer operation
FEES_TRANSFER = 411
# Fees for reveal operation
FEES_REVEAL = 368
# Minimal nanotez per gas unit, to calculate the fees
MINIMAL_NANOTEZ_PER_GAS_UNIT = 100

# Is var a worker
BAKER = False  # -> worker = False
WORKER = True

# Multiplier for Tez
MLTP = 1000000  # 1,000,000
