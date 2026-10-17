import os
import requests

# Dirección oficial de quema (Burn Address) de Ethereum / Shiba Inu
BURN_ADDRESS = "0x000000000000000000000000000000000000dead"
# Contrato oficial de Shiba Inu en Ethereum (ERC-20)
SHIB_CONTRACT = "0x95ad61b0a150d79219dcf64e1e6cc01f0b64c4ce"

# Nota: Puedes obtener una API Key gratuita en etherscan.io para evitar límites de consultas
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY", "YourApiKeyToken")

def get_shib_total_supply():
    """
    Obtiene el suministro total actual de SHIB en circulación o información del contrato.
    Utiliza la API pública de Etherscan.
    """
    try:
        url = (
            f"https://api.etherscan.io/api?module=stats&action=tokensupply"
            f"&contractaddress={SHIB_CONTRACT}&apikey={ETHERSCAN_API_KEY}"
        )
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if data["status"] == "1":
            # El suministro viene en Wei (con decimales, SHIB tiene 18 decimales)
            supply_wei = int(data["result"])
            supply_shib = supply_wei / (10 ** 18)
            return supply_shib
        return None
    except Exception as e:
        print(f"Error al obtener el suministro: {e}")
        return None

def get_burn_address_balance():
    """
    Consulta cuántos SHIB hay acumulados en la dirección de quema (Dead Address).
    """
    try:
        url = (
            f"https://api.etherscan.io/api?module=account&action=tokenbalance"
            f"&contractaddress={SHIB_CONTRACT}&address={BURN_ADDRESS}"
            f"&tag=latest&apikey={ETHERSCAN_API_KEY}"
        )
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if data["status"] == "1":
            balance_wei = int(data["result"])
            balance_shib = balance_wei / (10 ** 18)
            return balance_shib
        return 0.0
    except Exception as e:
        print(f"Error al obtener el balance quemado: {e}")
        return 0.0

def verify_burn_transaction(tx_hash):
    """
    Verifica si una transacción específica enviada por el usuario 
    efectivamente transfirió SHIB a la dirección de quema.
    """
    try:
        url = (
            f"https://api.etherscan.io/api?module=proxy&action=eth_getTransactionByHash"
            f"&txhash={tx_hash}&apikey={ETHERSCAN_API_KEY}"
        )
        response = requests.get(url, timeout=10)
        data = response.json()
        
        tx = data.get("result")
        if not tx:
            return {"success": False, "message": "Transacción no encontrada o inválida."}
        
        # Validar el destinatario (to)
        to_address = tx.get("to", "").lower()
        # Nota: En los contratos ERC-20, la transferencia llama al contrato SHIB, 
        # pero el input data codifica la dirección de destino. 
        # Una forma más sencilla para el usuario es validar los logs de la transacción (Receipt):
        
        receipt_url = (
            f"https://api.etherscan.io/api?module=proxy&action=eth_getTransactionReceipt"
            f"&txhash={tx_hash}&apikey={ETHERSCAN_API_KEY}"
        )
        receipt_resp = requests.get(receipt_url, timeout=10)
        receipt_data = receipt_resp.json().get("result")
        
        if not receipt_data:
            return {"success": False, "message": "La transacción aún está pendiente o no existe."}
            
        if receipt_data.get("status") == "0x1":
            return {
                "success": True, 
                "message": "¡Transacción verificada con éxito! Gracias por quemar SHIB.",
                "from": tx.get("from")
            }
        else:
            return {"success": False, "message": "La transacción falló en la blockchain."}
            
    except Exception as e:
        return {"success": False, "message": f"Error técnico al verificar: {str(e)}"}

