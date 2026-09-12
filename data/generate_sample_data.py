"""Generate project-specific demo data once the project idea is defined."""

from faker import Faker
import pandas as pd


def generate_sample_data() -> pd.DataFrame:
    """Return an empty data frame until a data model has been agreed."""
    fake = Faker()
    _ = fake  # Keep the generator ready for the future implementation.

    # Example business-record generation:
    # records = [
    #     {
    #         "name": fake.company(),
    #         "tax_id": fake.bothify(text="TN-########"),
    #         "sector": fake.random_element(["Agriculture", "Services", "Industry"]),
    #         "revenue": fake.random_int(min=10_000, max=5_000_000),
    #     }
    #     for _ in range(100)
    # ]
    # return pd.DataFrame(records)

    return pd.DataFrame()

