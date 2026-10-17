import streamlit as st
from utils import (
    get_shib_total_supply,
    get_burn_address_balance,
    verify_burn_transaction,
    load_leaderboard,
    save_burn_to_leaderboard,
    BURN_ADDRESS
)

# Configuración de la página
st.set_page_config(
    page_title="🔥 SHIB Burn Community Portal",
    page_icon="🔥",
    layout="wide"
)

st.title("🔥 Portal Comunitario de Quema de Shiba Inu")
st.subheader("Incentivando la reducción del suministro para fortalecer el ecosistema SHIB")

# --- SECCIÓN 1: Métricas de la Blockchain ---
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

# --- SECCIÓN 2: Registro de Quema (Proof of Burn) ---
st.divider()
st.header("⚡ Registra tu Quema (Proof of Burn)")
st.write("Realiza tu envío a la dirección de quema oficial usando MetaMask u otra wallet, y luego pega el **Hash de la transacción (TxHash)** abajo para acreditar tu aporte en el ranking.")

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

# --- SECCIÓN 3: Tabla de Líderes y Gráfico Nativo ---
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
        # Usamos el gráfico de barras nativo de Streamlit (sin librerías externas)
        chart_data = ranking_df.set_index("Alias")
        st.bar_chart(chart_data)
else:
    st.info("Aún no hay registros en esta sesión. ¡Sé el primero en quemar SHIB y aparecer en el ranking!")
