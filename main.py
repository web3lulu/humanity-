from web3 import Web3
from eth_account import Account
import json
import time
from web3.exceptions import ContractLogicError

def read_private_key():
    try:
        with open('keys.txt', 'r') as file:
            return file.read().strip()
    except FileNotFoundError:
        print("错误：找不到 keys.txt 文件")
        exit(1)
    except Exception as e:
        print(f"读取私钥时发生错误: {str(e)}")
        exit(1)

# 配置信息
PRIVATE_KEY = read_private_key()  # 从 keys.txt 文件读取私钥
REWARDS_CONTRACT = '0xa18f6FCB2Fd4884436d10610E69DB7BFa1bFe8C7'  # Rewards合约地址
RPC_URL = 'https://rpc.testnet.humanity.org'

# 其他配置
CHAIN_ID = 1942999413  # Humanity Testnet 的链 ID

# Rewards合约ABI，只包含我们需要的函数
ABI = [
    {
        "inputs": [],
        "name": "claimReward",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

def setup_web3():
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    account = Account.from_key(PRIVATE_KEY)
    return w3, account

def claim_reward(w3, account):
    try:
        # 创建合约实例
        contract = w3.eth.contract(address=REWARDS_CONTRACT, abi=ABI)
        
        # 先检查是否可以领取
        try:
            contract.functions.claimReward().call({'from': account.address})
        except ContractLogicError as e:
            error_msg = str(e)
            print("\n领取检查失败，原因：")
            if "Too early" in error_msg:
                print("- 距离上次领取时间未满24小时")
                try:
                    # 尝试获取上次领取时间
                    last_claim = contract.functions.lastClaimTime(account.address).call()
                    next_claim = last_claim + (24 * 60 * 60)
                    remaining = next_claim - int(time.time())
                    print(f"- 还需等待: {remaining//3600}小时{(remaining%3600)//60}分钟")
                except:
                    pass
            elif "no rewards available" in error_msg:
                print("- 当前没有可领取的奖励")
                print("- 请确认您是否满足领取条件")
            else:
                print(f"- 具体错误: {error_msg}")
            raise  # 继续抛出异常
            
        # 获取当前 gas 估算
        estimated_gas = contract.functions.claimReward().estimate_gas({'from': account.address})
        print(f"估算需要的 gas: {estimated_gas}")
        
        # 构建交易
        nonce = w3.eth.get_transaction_count(account.address)
        
        transaction = contract.functions.claimReward().build_transaction({
            'from': account.address,
            'nonce': nonce,
            'gas': 300000,
            'gasPrice': 0,  # Humanity Testnet 的 gas 价格为 0
            'chainId': CHAIN_ID
        })
        
        # 签名交易
        signed_txn = w3.eth.account.sign_transaction(transaction, PRIVATE_KEY)
        
        # 发送交易
        tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        print(f"交易已发送，交易哈希: {tx_hash.hex()}")
        
        # 等待交易确认
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt
        
    except Exception as e:
        print("\n交易失败，详细信息：")
        print(f"- 错误类型: {type(e).__name__}")
        print(f"- 错误消息: {str(e)}")
        if hasattr(e, 'args') and len(e.args) > 0:
            print(f"- 额外信息: {e.args[0]}")
        raise  # 继续抛出异常给主循环处理

def main():
    w3, account = setup_web3()
    print(f"使用账户地址: {account.address}")
    
    while True:
        try:
            print("\n开始尝试领取奖励...")
            receipt = claim_reward(w3, account)
            
            if receipt and receipt['status'] == 1:
                print("\n奖励领取成功！")
                print("等待24小时后进行下一次领取")
                time.sleep(24 * 60 * 60)
            else:
                print("\n交易失败或出错")
                print("5分钟后重试...")
                time.sleep(300)
                
        except Exception as e:
            print(f"\n程序运行错误:")
            print(f"- 错误类型: {type(e).__name__}")
            print(f"- 错误信息: {str(e)}")
            print("5分钟后重试...")
            time.sleep(300)

if __name__ == "__main__":
    main()
