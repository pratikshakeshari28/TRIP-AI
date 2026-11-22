import pandas as pd


def recommend_places(
    df,
    preference=None,
    budget=None,
    max_hours=None,
    min_rating=0,
    state=None,
    top_n=10
):
    

    result = df.copy()

    
    if preference:
        result = result[
            result["Type"].str.contains(
                preference, case=False, na=False
            )
        ]


    if budget is not None:
        result = result[
            result["Entrance Fee in INR"] <= budget
        ]

    
    if max_hours is not None:
        result = result[
            result["time needed to visit in hrs"] <= max_hours
        ]

    
    result = result[
        result["Google review rating"] >= min_rating
    ]

    
    if state:
        result = result[
            result["State"].str.contains(
                state, case=False, na=False
            )
        ]

    
    result = result.sort_values(
        by="Google review rating",
        ascending=False
    )

    columns = [
        "Name",
        "City",
        "State",
        "Type",
        "Entrance Fee in INR",
        "Google review rating"
    ]

    return result[columns].head(top_n)