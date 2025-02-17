
# Demonstrate how snowflake integer ids can be generated using snowflake-id package

from snowflake import SnowflakeGenerator, Snowflake

# Machine id needed to uniquely identify the machine generating the id can only be between 0-1023
MACHINE_ID = 23

# Epoch time is the time from which the id generation starts (ID generation will start from this time and work for the next 69x2 years)
EPOCH = 1739526270 # 2025-02-14 15:13:00


# Create a Snowflake ID generator instance with the machine id and epoch time
integer_id_generator = SnowflakeGenerator(
    instance=MACHINE_ID,
    epoch=EPOCH,
)


def generate_id():
    """Generate a Snowflake Integer ID"""
    return next(integer_id_generator)


def parse_id(int_id):
    """Parse a Snowflake ID and extract its components"""
    # Parse a Snowflake ID
    sf = Snowflake.parse(int_id, EPOCH)

    return sf



if __name__ == '__main__':
    # Generate a Snowflake ID in succession to simulate a service
    for i in range(1):
        # Generate an integer ID
        int_id = generate_id()
        print('Generated ID  :', int_id)

        # Parse the integer ID and see how it looks (helpful for debugging)
        parsed_id = parse_id(int_id)
        print('Parsed ID     :', parsed_id)