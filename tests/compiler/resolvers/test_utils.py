from graphqler.compiler.resolvers.utils import find_closest_string


def test_find_closest_string():
    strings = ["Comment", "Post", "User", "ListMetadata"]
    target = "createComment"
    expected_result = "Comment"
    assert find_closest_string(strings, target) == expected_result

    strings = ["Comment", "Post", "User", "ListMetadata", "Comments"]
    target = "createComments"
    expected_result = "Comments"
    assert find_closest_string(strings, target) == expected_result

    strings = ["Comment", "Post", "User", "ListMetadata", "Comments"]
    target = "asdf"
    expected_result = ""
    assert find_closest_string(strings, target) == expected_result


def test_find_closest_string_with_underscore():
    strings = ["Comment", "Post", "User", "ListMetadata"]
    target = "user_id"
    expected_result = "User"
    assert find_closest_string(strings, target) == expected_result
