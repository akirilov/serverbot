import random
import string

# Generate a sufficiently random password for the purposes of this thing
print(''.join(random.SystemRandom().choice(string.digits + string.ascii_uppercase + string.ascii_lowercase) for _ in range(32)))
