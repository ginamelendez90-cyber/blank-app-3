import os
import requests
import pandas as pd
from datetime import datetime
import streamlit as st

# ==========================================
# CONFIGURACIÓN Y FUNCIONES LÓGICAS (UTILS)
# ==========================================
BURN_ADDRESS = "0x000000000000000000000000000000000000dead"
SHIB_CONTRACT = "0x95ad61b0a150d79219dcf64e1e6cc01f0b64c4ce"
TRANSFER_EVENT_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY", "YourApiKeyToken")
LEADERBOARD_FILE = "leaderboard.csv"

def get_shib_total_supply():
    try:
        url = (
            f"https://api.etherscan.io/api?module=stats&action=tokensupply"
            f"&contractaddress={SHIB_CONTRACT}&apikey={ETHERSCAN_API_KEY}"
        )
        resp = requests.get(url, timeout=10).json()
        if resp.get("status") == "1":
            return int(resp["result"]) / (10 ** 18)
    except Exception:
        pass
    return 999_999_999_999_999.0

def get_burn_address_balance():
    try:
        url = (
            f"https://api.etherscan.io/api?module=account&action=tokenbalance"
            f"&contractaddress={SHIB_CONTRACT}&address={BURN_ADDRESS}"
            f"&tag=latest&apikey={ETHERSCAN_API_KEY}"
        )
        resp = requests.get(url, timeout=10).json()
        if resp.get("status") == "1":
            return int(resp["result"]) / (10 ** 18)
    except Exception:
        pass
    return 0.0

def verify_burn_transaction(tx_hash):
    try:
        tx_hash = tx_hash.strip()
        url = (
            f"https://api.etherscan.io/api?module=proxy&action=eth_getTransactionReceipt"
            f"&txhash={tx_hash}&apikey={ETHERSCAN_API_KEY}"
        )
        resp = requests.get(url, timeout=10).json()
        receipt = resp.get("result")

        if not receipt:
            return {"success": False, "message": "Transacción no encontrada o aún no ha sido confirmada."}

        if receipt.get("status") != "0x1":
            return {"success": False, "message": "La transacción falló en la red de Ethereum."}

        shib_burned = 0.0
        sender_address = receipt.get("from", "Desconocido")

        for log in receipt.get("logs", []):
            if log.get("address", "").lower() == SHIB_CONTRACT.lower():
                topics = log.get("topics", [])
                if len(topics) >= 3 and topics[0] == TRANSFER_EVENT_TOPIC:
                    to_address = "0x" + topics[2][-40:].lower()
                    if to_address == BURN_ADDRESS.lower():
                        raw_amount = int(log.get("data", "0x0"), 16)
                        shib_burned += raw_amount / (10 ** 18)

        if shib_burned > 0:
            return {
                "success": True,
                "message": f"¡Verificado exitosamente! Se quemaron {shib_burned:,.2f} SHIB.",
                "amount": shib_burned,
                "wallet": sender_address
            }
        else:
            return {
                "success": False,
                "message": "La transacción es válida, pero no incluye un envío de SHIB a la dirección de quema oficial."
            }
    except Exception as e:
        return {"success": False, "message": f"Error al procesar la verificación: {str(e)}"}

def load_leaderboard():
    if os.path.exists(LEADERBOARD_FILE):
        try:
            return pd.read_csv(LEADERBOARD_FILE)
        except Exception:
            pass
    return pd.DataFrame(columns=["Alias", "Billetera", "Monto_Quemado_SHIB", "Fecha", "TxHash"])

def save_burn_to_leaderboard(alias, wallet, amount, tx_hash):
    df = load_leaderboard()
    if not df.empty and tx_hash in df["TxHash"].values:
        return False, "Esta transacción ya ha sido registrada previamente."

    new_row = {
        "Alias": alias if alias.strip() else f"{wallet[:6]}...{wallet[-4:]}",
        "Billetera": wallet,
        "Monto_Quemado_SHIB": amount,
        "Fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "TxHash": tx_hash
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_csv(LEADERBOARD_FILE, index=False)
    return True, "¡Registro guardado con éxito en el Muro de Honor!"

# ==========================================
# INTERFAZ DE USUARIO (STREAMLIT)
# ==========================================
st.set_page_config(
    page_title="🔥 SHIB Burn Community Portal",
    page_icon="🔥",
    layout="wide"
)

st.title("🔥 Portal Comunitario de Quema de Shiba Inu")
st.subheader("Incentivando la reducción del suministro para fortalecer el ecosistema SHIB")

# --- SECCIÓN 1: Métricas ---
st.divider()
col1, col2, col3 = st.columns(3)

with st.spinner("Cargando datos en tiempo real de la blockchain..."):
    total_supply = get_shib_total_supply()
    total_burned = get_burn_address_balance()
    burn_percentage = (total_burned / (total_supply + total_burned)) * 100 if total_supply else 0

with col1:
    st.metric("🔥 Total SHIB Quemado (Dead Address)", f"{total_burned:,.0f}")
with col2:
    st.metric("📦 Suministro Circulante Estimado", f"{total_supply:,.0f}")
with col3:
    st.metric("📊 % Total del Suministro Quemado", f"{burn_percentage:.2f}%")

st.info(f"💡 **Dirección de Quema Oficial:** `{BURN_ADDRESS}`")

# --- SECCIÓN 2: Registro de Quema ---
st.divider()
st.header("⚡ Registra tu Quema (Proof of Burn)")
st.write("Realiza tu envío a la dirección de quema oficial y pega el **Hash de la transacción (TxHash)** abajo.")

col_form1, col_form2 = st.columns([2, 1])

with col_form1:
    tx_hash_input = st.text_input("Hash de la Transacción (TxHash):", placeholder="0x...")
    user_alias = st.text_input("Tu Alias / Nombre (Opcional):", placeholder="Ej: ShibArmyHero")

with col_form2:
    st.write(" ")
    st.write(" ")
    btn_verify = st.button("🔥 Verificar y Registrar Quema", use_container_width=True)

if btn_verify:
    if not tx_hash_input:
        st.warning("Por favor, ingresa un Hash de transacción válido.")
    else:
        with st.spinner("Verificando transacción en la red Ethereum..."):
            res = verify_burn_transaction(tx_hash_input)
            if res["success"]:
                st.success(res["message"])
                saved, save_msg = save_burn_to_leaderboard(
                    alias=user_alias,
                    wallet=res["wallet"],
                    amount=res["amount"],
                    tx_hash=tx_hash_input
                )
                if saved:
                    st.balloons()
                    st.success(save_msg)
                else:
                    st.warning(save_msg)
            else:
                st.error(res["message"])

# --- SECCIÓN 3: Tabla de Líderes ---
st.divider()
st.header("🏆 Tabla de Líderes de la Comunidad")

df_leaderboard = load_leaderboard()

if not df_leaderboard.empty:
    ranking_df = (
        df_leaderboard.groupby("Alias")["Monto_Quemado_SHIB"]
        .sum()
        .reset_index()
        .sort_values(by="Monto_Quemado_SHIB", ascending=False)
    )

    col_table, col_chart = st.columns(2)

    with col_table:
        st.subheader("Top Contribuyentes")
        st.dataframe(
            ranking_df.style.format({"Monto_Quemado_SHIB": "{:,.0f}"}),
            use_container_width=True,
            hide_index=True
        )

    with col_chart:
        st.subheader("Visualización de Quemas")
        chart_data = ranking_df.set_index("Alias")
        st.bar_chart(chart_data)
else:
    st.info("Aún no hay registros en esta sesión. ¡Sé el primero en quemar SHIB y aparecer en el ranking!")
