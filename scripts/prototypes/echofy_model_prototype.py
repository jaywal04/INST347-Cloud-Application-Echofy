import math

ratings = {
    "Nathan": {
        "One Dance": 5,
        "SICKO MODE": 4,
        "The Less I Know The Better": 5,
        "Wish You Were Here": 4,
    },
    "Aiden": {
        "One Dance": 4,
        "SICKO MODE": 5,
        "The Less I Know The Better": 2,
        "Nights": 5,
    },
    "Jay": {
        "One Dance": 2,
        "Wish You Were Here": 5,
        "The Less I Know The Better": 4,
        "Money Trees": 4,
    },
    "Andrew": {
        "SICKO MODE": 3,
        "Wish You Were Here": 5,
        "Nights": 4,
        "Money Trees": 5,
    },
}

songs = sorted({song for user_ratings in ratings.values() for song in user_ratings})


def build_vector(user):
    return [ratings[user].get(song, 0) for song in songs]


def cosine_similarity(user_a, user_b):
    a = build_vector(user_a)
    b = build_vector(user_b)

    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(y * y for y in b))

    if mag_a == 0 or mag_b == 0:
        return 0

    return dot / (mag_a * mag_b)


def recommend_songs(target_user, top_n=3):
    scores = {}
    similarity_totals = {}

    for other_user in ratings:
        if other_user == target_user:
            continue

        similarity = cosine_similarity(target_user, other_user)

        for song, rating in ratings[other_user].items():
            if song in ratings[target_user]:
                continue

            scores[song] = scores.get(song, 0) + similarity * rating
            similarity_totals[song] = similarity_totals.get(song, 0) + similarity

    recommendations = []
    for song in scores:
        predicted_score = scores[song] / similarity_totals[song]
        recommendations.append((song, round(predicted_score, 2)))

    recommendations.sort(key=lambda item: item[1], reverse=True)
    return recommendations[:top_n]


target_user = "Nathan"

print("Echofy Model Prototype")
print("-" * 24)
print(f"Target user: {target_user}")
print("\nUser similarity scores:")
for user in ratings:
    if user == target_user:
        continue
    print(f"  {user}: {cosine_similarity(target_user, user):.3f}")

print("\nRecommended songs:")
for song, score in recommend_songs(target_user):
    print(f"  {song} -> predicted rating: {score}/5")
