"""
Interface Streamlit pour la plateforme MAR
Interface utilisateur moderne et intuitive
"""

import streamlit as st
import requests
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from dotenv import load_dotenv

# Chargement des variables d'environnement
load_dotenv()

# Configuration
MAR_API_URL = os.getenv("MAR_API_URL", "http://localhost:8000")
API_KEY = os.getenv("MAR_API_KEY", "")

# Configuration de la page
st.set_page_config(
    page_title="MAR Platform",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personnalisé
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .agent-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        margin: 1rem 0;
    }
    
    .metric-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        margin: 0.5rem 0;
    }
    
    .chat-message {
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
    }
    
    .user-message {
        background: #e3f2fd;
        border-left: 4px solid #2196f3;
    }
    
    .assistant-message {
        background: #f3e5f5;
        border-left: 4px solid #9c27b0;
    }
    
    .agent-workflow {
        background: #fff3e0;
        border: 1px solid #ff9800;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)


class MARInterface:
    """Interface principale pour la plateforme MAR"""
    
    def __init__(self):
        self.api_url = MAR_API_URL
        self.headers = {"Authorization": f"Bearer {API_KEY}"} if API_KEY else {}
        
        # Initialisation de l'état de session
        if "messages" not in st.session_state:
            st.session_state.messages = []
        if "workflow_history" not in st.session_state:
            st.session_state.workflow_history = []
    
    def run(self):
        """Lance l'interface principale"""
        # Header
        st.markdown('<h1 class="main-header">🤖 MAR Platform</h1>', unsafe_allow_html=True)
        st.markdown("**Multi-Agent RAG Platform** - Intelligence artificielle locale et observable")
        
        # Sidebar pour navigation
        with st.sidebar:
            st.title("Navigation")
            page = st.selectbox(
                "Choisir une page",
                ["💬 Chat", "📊 Dashboard", "📁 Documents", "🔧 Configuration", "📈 Monitoring"]
            )
        
        # Routing des pages
        if page == "💬 Chat":
            self.chat_page()
        elif page == "📊 Dashboard":
            self.dashboard_page()
        elif page == "📁 Documents":
            self.documents_page()
        elif page == "🔧 Configuration":
            self.config_page()
        elif page == "📈 Monitoring":
            self.monitoring_page()
    
    def chat_page(self):
        """Page de chat principal"""
        st.header("💬 Chat avec les Agents MAR")
        
        # Configuration du chat
        col1, col2 = st.columns([3, 1])
        
        with col2:
            st.subheader("Configuration")
            
            max_docs = st.slider("Documents max", 1, 20, 5)
            include_validation = st.checkbox("Validation par Critic", True)
            show_workflow = st.checkbox("Afficher le workflow", True)
            
            # Sélection des agents
            st.subheader("Agents actifs")
            agents = {
                "🔍 Retriever": st.checkbox("Retriever", True),
                "📝 Summarizer": st.checkbox("Summarizer", True),
                "🧠 Synthesizer": st.checkbox("Synthesizer", True),
                "🔎 Critic": st.checkbox("Critic", include_validation),
                "📊 Ranker": st.checkbox("Ranker", False)
            }
        
        with col1:
            # Zone de chat
            chat_container = st.container()
            
            with chat_container:
                # Affichage des messages
                for message in st.session_state.messages:
                    if message["role"] == "user":
                        st.markdown(f"""
                        <div class="chat-message user-message">
                            <strong>👤 Vous:</strong><br>
                            {message["content"]}
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div class="chat-message assistant-message">
                            <strong>🤖 Assistant MAR:</strong><br>
                            {message["content"]}
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Afficher le workflow si disponible
                        if show_workflow and "workflow" in message:
                            self.display_workflow(message["workflow"])
            
            # Zone de saisie
            with st.container():
                st.markdown("---")
                user_input = st.text_area(
                    "Votre question:",
                    placeholder="Posez une question aux agents MAR...",
                    height=100
                )
                
                col_send, col_clear = st.columns([1, 1])
                
                with col_send:
                    if st.button("🚀 Envoyer", type="primary", use_container_width=True):
                        if user_input.strip():
                            self.process_query(user_input, max_docs, include_validation, agents)
                
                with col_clear:
                    if st.button("🗑️ Vider le chat", use_container_width=True):
                        st.session_state.messages = []
                        st.rerun()
    
    def process_query(self, query: str, max_docs: int, include_validation: bool, agents: Dict[str, bool]):
        """Traite une requête utilisateur"""
        # Ajouter le message utilisateur
        st.session_state.messages.append({"role": "user", "content": query})
        
        # Préparer la requête
        active_agents = [agent for agent, active in agents.items() if active]
        
        payload = {
            "query": query,
            "max_documents": max_docs,
            "include_validation": include_validation,
            "agents": active_agents
        }
        
        # Spinner pendant le traitement
        with st.spinner("🤖 Les agents MAR travaillent..."):
            try:
                # Simulation d'appel API (remplacer par le vrai appel)
                response = self.simulate_mar_response(query, payload)
                
                # Ajouter la réponse
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": response["answer"],
                    "workflow": response.get("workflow", [])
                })
                
                # Ajouter au workflow history
                st.session_state.workflow_history.append(response)
                
            except Exception as e:
                st.error(f"Erreur lors du traitement: {str(e)}")
        
        st.rerun()
    
    def simulate_mar_response(self, query: str, payload: Dict) -> Dict[str, Any]:
        """Simule une réponse de l'API MAR (à remplacer par le vrai appel)"""
        import time
        import random
        
        # Simulation du workflow
        workflow = [
            {
                "agent": "Retriever",
                "action": "Recherche vectorielle",
                "status": "completed",
                "duration": 0.5,
                "results": f"Trouvé {random.randint(3, 8)} documents pertinents"
            },
            {
                "agent": "Summarizer", 
                "action": "Résumé des documents",
                "status": "completed",
                "duration": 1.2,
                "results": "Résumés générés avec succès"
            },
            {
                "agent": "Synthesizer",
                "action": "Synthèse contextuelle",
                "status": "completed", 
                "duration": 2.1,
                "results": "Réponse synthétisée"
            }
        ]
        
        if payload.get("include_validation"):
            workflow.append({
                "agent": "Critic",
                "action": "Validation de la réponse",
                "status": "completed",
                "duration": 0.8,
                "results": f"Score de qualité: {random.randint(85, 98)}/100"
            })
        
        # Simulation de latence
        time.sleep(1)
        
        return {
            "answer": f"""
Voici une réponse simulée pour votre question: "{query}"

Cette réponse a été générée par les agents MAR en analysant {random.randint(3, 8)} documents pertinents. 
Les agents ont collaboré pour vous fournir une réponse complète et vérifiée.

**Points clés:**
- Analyse effectuée par {len([a for a in payload['agents'] if payload['agents']])} agents
- Documents analysés: {payload['max_documents']} maximum
- Validation: {'Activée' if payload['include_validation'] else 'Désactivée'}

*Note: Ceci est une simulation. La vraie plateforme MAR utilisera les agents réels.*
            """,
            "workflow": workflow,
            "metadata": {
                "query": query,
                "timestamp": datetime.now().isoformat(),
                "total_duration": sum(step["duration"] for step in workflow)
            }
        }
    
    def display_workflow(self, workflow: List[Dict]):
        """Affiche le workflow des agents"""
        st.markdown('<div class="agent-workflow">', unsafe_allow_html=True)
        st.markdown("**🔄 Workflow des Agents:**")
        
        for i, step in enumerate(workflow):
            status_icon = "✅" if step["status"] == "completed" else "⏳"
            duration = step.get("duration", 0)
            
            st.markdown(f"""
            **{i+1}. {status_icon} {step['agent']}** - {step['action']}  
            ⏱️ {duration:.1f}s | 📋 {step['results']}
            """)
        
        total_time = sum(step.get("duration", 0) for step in workflow)
        st.markdown(f"**⏱️ Durée totale: {total_time:.1f}s**")
        st.markdown('</div>', unsafe_allow_html=True)
    
    def dashboard_page(self):
        """Page de dashboard avec métriques"""
        st.header("📊 Dashboard MAR")
        
        # Métriques principales
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("🗂️ Documents", "1,234", "+56 aujourd'hui")
        
        with col2:
            st.metric("🤖 Requêtes traitées", "5,678", "+23 cette heure")
        
        with col3:
            st.metric("⚡ Temps moyen", "2.3s", "-0.2s")
        
        with col4:
            st.metric("✅ Taux de réussite", "97.8%", "+1.2%")
        
        # Graphiques
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📈 Requêtes par heure")
            # Données simulées
            hours = list(range(24))
            queries = [20, 15, 10, 8, 12, 25, 45, 67, 89, 76, 54, 62, 
                      78, 85, 92, 88, 76, 69, 58, 47, 38, 32, 28, 22]
            
            fig = px.line(x=hours, y=queries, title="Requêtes par heure")
            fig.update_layout(xaxis_title="Heure", yaxis_title="Nombre de requêtes")
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("🤖 Performance des agents")
            agents = ["Retriever", "Summarizer", "Synthesizer", "Critic", "Ranker"]
            scores = [95, 92, 88, 96, 85]
            
            fig = px.bar(x=agents, y=scores, title="Scores de performance")
            fig.update_layout(xaxis_title="Agents", yaxis_title="Score (%)")
            st.plotly_chart(fig, use_container_width=True)
        
        # Historique des workflows
        st.subheader("📊 Historique des workflows")
        if st.session_state.workflow_history:
            df_workflows = pd.DataFrame([
                {
                    "Timestamp": wf["metadata"]["timestamp"],
                    "Requête": wf["metadata"]["query"][:50] + "...",
                    "Durée (s)": wf["metadata"]["total_duration"],
                    "Agents": len(wf["workflow"])
                }
                for wf in st.session_state.workflow_history[-10:]  # 10 derniers
            ])
            st.dataframe(df_workflows, use_container_width=True)
        else:
            st.info("Aucun workflow dans l'historique. Lancez une requête dans le chat.")
    
    def documents_page(self):
        """Page de gestion des documents"""
        st.header("📁 Gestion des Documents")
        
        # Upload de documents
        st.subheader("📤 Télécharger des documents")
        
        uploaded_files = st.file_uploader(
            "Sélectionnez vos documents",
            accept_multiple_files=True,
            type=['pdf', 'txt', 'docx', 'md']
        )
        
        if uploaded_files:
            col1, col2 = st.columns([3, 1])
            
            with col1:
                for file in uploaded_files:
                    st.write(f"📄 {file.name} ({file.size} bytes)")
            
            with col2:
                if st.button("🚀 Traiter les documents", type="primary"):
                    with st.spinner("Traitement en cours..."):
                        # Simulation du traitement
                        import time
                        time.sleep(2)
                        st.success(f"✅ {len(uploaded_files)} documents traités!")
        
        # Liste des documents existants
        st.subheader("📋 Documents dans le vector store")
        
        # Simulation d'une liste de documents
        documents_data = [
            {"ID": "doc_001", "Nom": "Guide utilisateur.pdf", "Chunks": 15, "Taille": "2.3 MB", "Date": "2024-01-15"},
            {"ID": "doc_002", "Nom": "Manuel technique.docx", "Chunks": 23, "Taille": "1.8 MB", "Date": "2024-01-14"},
            {"ID": "doc_003", "Nom": "FAQ.txt", "Chunks": 8, "Taille": "156 KB", "Date": "2024-01-13"},
        ]
        
        df_docs = pd.DataFrame(documents_data)
        st.dataframe(df_docs, use_container_width=True)
        
        # Actions sur les documents
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔄 Actualiser la liste"):
                st.rerun()
        
        with col2:
            if st.button("📊 Statistiques détaillées"):
                st.info("Fonctionnalité à implémenter")
        
        with col3:
            if st.button("🗑️ Nettoyer les documents"):
                st.warning("⚠️ Cette action supprimera tous les documents orphelins")
    
    def config_page(self):
        """Page de configuration"""
        st.header("🔧 Configuration MAR")
        
        # Configuration des agents
        st.subheader("🤖 Configuration des Agents")
        
        with st.expander("Retriever Agent"):
            max_docs = st.slider("Documents maximum à récupérer", 1, 50, 10)
            similarity_threshold = st.slider("Seuil de similarité", 0.0, 1.0, 0.7)
            st.text_area("Prompt système", "Vous êtes un agent de récupération...")
        
        with st.expander("Summarizer Agent"):
            summary_length = st.selectbox("Longueur du résumé", ["Court", "Moyen", "Long"])
            summary_style = st.selectbox("Style", ["Bullet points", "Paragraphe", "Structuré"])
        
        with st.expander("Synthesizer Agent"):
            creativity = st.slider("Créativité", 0.0, 1.0, 0.5)
            context_window = st.number_input("Fenêtre de contexte", 1000, 8000, 4000)
        
        # Configuration du Vector Store
        st.subheader("🗄️ Vector Store")
        vector_store_type = st.selectbox("Type de vector store", ["FAISS", "Chroma"])
        embedding_model = st.selectbox("Modèle d'embedding", 
                                     ["sentence-transformers/all-MiniLM-L6-v2", 
                                      "sentence-transformers/all-mpnet-base-v2"])
        
        # Configuration LLM
        st.subheader("🧠 Modèle LLM")
        llm_model = st.selectbox("Modèle Ollama", ["llama3", "mistral", "phi3"])
        temperature = st.slider("Température", 0.0, 1.0, 0.7)
        max_tokens = st.number_input("Tokens maximum", 100, 4000, 2000)
        
        # Boutons d'action
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("💾 Sauvegarder", type="primary"):
                st.success("✅ Configuration sauvegardée!")
        
        with col2:
            if st.button("🔄 Réinitialiser"):
                st.info("Configuration réinitialisée aux valeurs par défaut")
        
        with col3:
            if st.button("🧪 Tester la configuration"):
                with st.spinner("Test en cours..."):
                    import time
                    time.sleep(2)
                    st.success("✅ Configuration validée!")
    
    def monitoring_page(self):
        """Page de monitoring avancé"""
        st.header("📈 Monitoring & Observabilité")
        
        # Métriques système
        st.subheader("💻 Métriques Système")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Gauge CPU
            fig_cpu = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = 65,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "CPU Usage (%)"},
                gauge = {
                    'axis': {'range': [None, 100]},
                    'bar': {'color': "darkblue"},
                    'steps': [
                        {'range': [0, 50], 'color': "lightgray"},
                        {'range': [50, 80], 'color': "yellow"},
                        {'range': [80, 100], 'color': "red"}
                    ]
                }
            ))
            fig_cpu.update_layout(height=200)
            st.plotly_chart(fig_cpu, use_container_width=True)
        
        with col2:
            # Gauge Memory
            fig_mem = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = 78,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "Memory Usage (%)"},
                gauge = {
                    'axis': {'range': [None, 100]},
                    'bar': {'color': "darkgreen"},
                    'steps': [
                        {'range': [0, 50], 'color': "lightgray"},
                        {'range': [50, 80], 'color': "yellow"},
                        {'range': [80, 100], 'color': "red"}
                    ]
                }
            ))
            fig_mem.update_layout(height=200)
            st.plotly_chart(fig_mem, use_container_width=True)
        
        with col3:
            # Gauge Disk
            fig_disk = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = 45,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "Disk Usage (%)"},
                gauge = {
                    'axis': {'range': [None, 100]},
                    'bar': {'color': "darkorange"},
                    'steps': [
                        {'range': [0, 50], 'color': "lightgray"},
                        {'range': [50, 80], 'color': "yellow"},
                        {'range': [80, 100], 'color': "red"}
                    ]
                }
            ))
            fig_disk.update_layout(height=200)
            st.plotly_chart(fig_disk, use_container_width=True)
        
        # Logs en temps réel
        st.subheader("📋 Logs en Temps Réel")
        
        log_container = st.container()
        with log_container:
            # Simulation de logs
            logs = [
                "2024-01-15 14:30:25 [INFO] Nouvelle requête reçue: 'Comment fonctionne...?'",
                "2024-01-15 14:30:26 [INFO] Retriever Agent: Recherche vectorielle démarrée",
                "2024-01-15 14:30:27 [INFO] Retriever Agent: 5 documents trouvés",
                "2024-01-15 14:30:28 [INFO] Summarizer Agent: Résumé en cours...",
                "2024-01-15 14:30:30 [INFO] Synthesizer Agent: Génération de la réponse",
                "2024-01-15 14:30:32 [INFO] Critic Agent: Validation score: 94/100",
                "2024-01-15 14:30:33 [INFO] Réponse envoyée avec succès"
            ]
            
            for log in logs:
                if "[ERROR]" in log:
                    st.error(log)
                elif "[WARNING]" in log:
                    st.warning(log)
                else:
                    st.text(log)
        
        # Liens vers Grafana/Prometheus
        st.subheader("🔗 Outils Externes")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📊 Ouvrir Grafana", use_container_width=True):
                st.markdown("[Grafana Dashboard](http://localhost:3000)", unsafe_allow_html=True)
        
        with col2:
            if st.button("🎯 Ouvrir Prometheus", use_container_width=True):
                st.markdown("[Prometheus Metrics](http://localhost:9090)", unsafe_allow_html=True)
        
        with col3:
            if st.button("🔍 Ouvrir Kibana", use_container_width=True):
                st.markdown("[Kibana Logs](http://localhost:5601)", unsafe_allow_html=True)


def main():
    """Point d'entrée principal"""
    interface = MARInterface()
    interface.run()


if __name__ == "__main__":
    main()
