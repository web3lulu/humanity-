from web3 import Web3
from eth_account import Account
import json
import time
from web3.exceptions import ContractLogicError
import random
from datetime import datetime


def read_private_keys():
    """读取所有私钥并编号"""
    private_keys = []
    with open('keys.txt', 'r') as file:
        for index, line in enumerate(file, 1):
            if line.strip():
                print(f"读取第 {index} 个私钥")
                private_keys.append(line.strip())
    return private_keys


def log_failure(address, reward_type):
    """记录失败信息到日志"""
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open('log.txt', 'a', encoding='utf-8') as file:
        file.write(f"{current_time} - 地址 {address} {reward_type}领取失败\n")


# 配置信息
REWARDS_CONTRACT = '0xa18f6FCB2Fd4884436d10610E69DB7BFa1bFe8C7'
RPC_URL = 'https://rpc.testnet.humanity.org'
CHAIN_ID = 1942999413

# 更新 ABI，添加 buffer 相关函数
ABI = [
    {
        "inputs": [],
        "name": "claimReward",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "claimBuffer",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "address", "name": "user", "type": "address"}],
        "name": "userBuffer",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]


def check_buffer(w3, contract, address):
    """检查是否有推荐奖励"""
    try:
        buffer = contract.functions.userBuffer(address).call()
        print(f"推荐奖励检查结果: {buffer}")  # 显示检查结果
        return buffer > 0
    except Exception:
        print("检查推荐奖励失败")
        return False


def claim_daily_reward(w3, account, private_key, contract):
    """领取每日奖励"""
    try:
        try:
            contract.functions.claimReward().call({'from': account.address})
        except ContractLogicError as e:
            print(f"每日奖励检查失败")
            raise

        # 添加 gas 估算
        estimated_gas = contract.functions.claimReward().estimate_gas({'from': account.address})
        print(f"每日奖励预估 gas: {estimated_gas}")

        nonce = w3.eth.get_transaction_count(account.address)
        transaction = contract.functions.claimReward().build_transaction({
            'from': account.address,
            'nonce': nonce,
            'gas': estimated_gas,  # 使用估算的 gas
            'gasPrice': 0,
            'chainId': CHAIN_ID
        })

        signed_txn = w3.eth.account.sign_transaction(transaction, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        print(f"每日奖励交易已发送，哈希: {tx_hash.hex()}")

        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        if receipt['status'] == 1:
            print(f"实际使用 gas: {receipt['gasUsed']}")  # 显示实际使用的 gas
        return receipt
    except Exception as e:
        print(f"每日奖励领取失败: {str(e)}")
        return None


def claim_referral_reward(w3, account, private_key, contract):
    """领取推荐奖励"""
    try:
        # 添加 gas 估算
        estimated_gas = contract.functions.claimBuffer().estimate_gas({'from': account.address})
        print(f"推荐奖励预估 gas: {estimated_gas}")

        nonce = w3.eth.get_transaction_count(account.address)
        transaction = contract.functions.claimBuffer().build_transaction({
            'from': account.address,
            'nonce': nonce,
            'gas': estimated_gas,  # 使用估算的 gas
            'gasPrice': 0,
            'chainId': CHAIN_ID
        })

        signed_txn = w3.eth.account.sign_transaction(transaction, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        print(f"推荐奖励交易已发送，哈希: {tx_hash.hex()}")

        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        if receipt['status'] == 1:
            print(f"实际使用 gas: {receipt['gasUsed']}")  # 显示实际使用的 gas
        return receipt
    except Exception as e:
        print(f"\n推荐奖励领取失败: {str(e)}")
        log_failure(account.address, "推荐奖励")
        return None


def main():
    private_keys = read_private_keys()
    print(f"总共读取到 {len(private_keys)} 个私钥")
    random.shuffle(private_keys)
    print("已随机打乱执行顺序")

    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    contract = w3.eth.contract(address=REWARDS_CONTRACT, abi=ABI)

    for i, private_key in enumerate(private_keys, 1):
        try:
            account = Account.from_key(private_key)
            print(f"\n正在处理第 {i}/{len(private_keys)} 个钱包")
            print(f"钱包地址: {account.address}")

            # 检查并领取每日奖励
            receipt = claim_daily_reward(w3, account, private_key, contract)
            if receipt and receipt['status'] == 1:
                print("每日奖励领取成功！")
            else:
                log_failure(account.address, "每日奖励")

            wait_time = random.randint(1, 3)
            time.sleep(wait_time)

            # 检查是否有推荐奖励
            if check_buffer(w3, contract, account.address):
                print("发现推荐奖励，尝试领取...")
                buffer_receipt = claim_referral_reward(w3, account, private_key, contract)
                if buffer_receipt and buffer_receipt['status'] == 1:
                    print("推荐奖励领取成功！")
                else:
                    print("推荐奖励领取失败")
                    log_failure(account.address, "推荐奖励")
            else:
                print("没有可领取的推荐奖励")

            if i < len(private_keys):
                wait_time = random.randint(30, 60)
                print(f"等待 {wait_time} 秒后处理下一个钱包...")
                time.sleep(wait_time)

        except Exception as e:
            print(f"处理失败: {str(e)}")
            log_failure(account.address, "处理")

    print("\n所有钱包处理完成")


if __name__ == "__main__":
    main()