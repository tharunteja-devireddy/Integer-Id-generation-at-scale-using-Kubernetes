

from snowflake import SnowflakeGenerator, Snowflake


WORKER_ID = 0
DATACENTER_ID = 0
MACHINE_ID = (DATACENTER_ID << 5) | WORKER_ID

EPOCH = 1739526270 # 2025-02-14 15:13:00


integer_id_generator = SnowflakeGenerator(
    instance=MACHINE_ID,
    epoch=EPOCH,
)


def generate_id():
    return next(integer_id_generator)

def parse_id(int_id):
    # Parse a Snowflake ID
    sf = Snowflake.parse(int_id, EPOCH)

    print(sf)



if __name__ == '__main__':
    int_id = generate_id()
    print(int_id)
    parse_id(int_id)