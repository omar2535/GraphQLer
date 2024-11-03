from graphqler.fuzzer.engine.retrier.utils import find_block_end, remove_lines_within_range

test_payload = """
mutation {
  createTransaction(
    amount: 3.1415
    currencyID: "6b64de06-09f9-492e-be5e-5be1203e249a"
    payerID: "1234567890"
    walletID: "18598551-f720-47a8-b837-eff2e1a5be6b"
  ) {
    id
    amount
    rate
    payer {
      id
      firstName
      lastName
      description
      wallets {
        id
        name
        currency {
          id
          abbreviation
          symbol
          rate
          country
        }
        transactions {
          id
          amount
          rate
          payer {
            id
            firstName
            lastName
            description
            wallets {
              id
              name
              currency {
                id
                abbreviation
                symbol
                rate
                country
              }
              balance
            }
          }
          description
          location {
            id
            lat
            lng
            name
          }
          timestamp
        }
        balance
      }
    }
    description
    location {
      id
      lat
      lng
      name
    }
    timestamp
  }
}
"""

resulting_payload = """
mutation {
  createTransaction(
    amount: 3.1415
    currencyID: "6b64de06-09f9-492e-be5e-5be1203e249a"
    payerID: "1234567890"
    walletID: "18598551-f720-47a8-b837-eff2e1a5be6b"
  ) {
    id
    amount
    rate
    description
    location {
      id
      lat
      lng
      name
    }
    timestamp
  }
}
"""


def test_find_block_end():
    assert find_block_end(test_payload, 11) == 59


def test_remove_lines_within_range():
    start_line = 11
    block_end_number = find_block_end(test_payload, start_line)
    assert remove_lines_within_range(test_payload, start_line, block_end_number) == resulting_payload
