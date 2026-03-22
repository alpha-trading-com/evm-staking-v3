"""Initialize staking gate hash and toggle staking/unstaking on the contract."""
from app.services.evm_service import get_w3_account_contract, receipt_to_dict, run_quiet
from evm.stake_wrap import set_staking_gate_password_hash, set_staking_unstaking_enabled


def do_init_staking_gate_password(plain_password: str) -> dict:
    w3, account, contract_address, contract = get_w3_account_contract()
    receipt = run_quiet(
        set_staking_gate_password_hash,
        w3,
        account,
        contract_address,
        plain_password,
        contract=contract,
    )
    return {"ok": True, "receipt": receipt_to_dict(receipt)}


def do_set_staking_unstaking_enabled(enabled: bool, password: str) -> dict:
    w3, account, contract_address, contract = get_w3_account_contract()
    receipt = run_quiet(
        set_staking_unstaking_enabled,
        w3,
        account,
        contract_address,
        enabled,
        password,
        contract=contract,
    )
    return {"ok": True, "receipt": receipt_to_dict(receipt)}
