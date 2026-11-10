#!/usr/bin/env python3
"""
Script para processar todos os filmes existentes e pré-popular dados
"""

import requests
import time
import json
from datetime import datetime

BASE_URL = "http://localhost:5001/api"


def process_all_existing_movies():
    """Processa todos os filmes existentes para pré-popular dados"""

    print("🎬 Processando todos os filmes existentes...")
    print("=" * 60)

    start_time = time.time()

    # 1. Busca estatísticas atuais
    print("📊 Verificando estatísticas atuais...")
    stats_response = requests.get(f"{BASE_URL}/prepopulate/stats")

    if stats_response.status_code == 200:
        stats = stats_response.json()
        print(f"   📈 Filmes: {stats.get('total_movies', 0)}")
        print(f"   🎭 Diretores: {stats.get('total_directors', 0)}")
        print(f"   🎵 Trilhas sonoras: {stats.get('total_soundtracks', 0)}")
        print(f"   📊 Cobertura geral: {stats.get('overall_coverage', 0)}%")
    else:
        print("⚠️ Não foi possível obter estatísticas")

    # 2. Inicia pré-população
    print(f"\n🚀 Iniciando pré-população...")
    prepopulate_start = time.time()

    prepopulate_response = requests.post(
        f"{BASE_URL}/prepopulate/all", json={"language": "pt", "max_workers": 3}
    )

    prepopulate_time = time.time() - prepopulate_start

    if prepopulate_response.status_code == 200:
        result = prepopulate_response.json()
        print(f"✅ Pré-população concluída em {prepopulate_time:.2f}s")
        print(f"   📊 Total processados: {result.get('total_movies', 0)}")
        print(f"   ✅ Sucessos: {result.get('success_count', 0)}")
        print(f"   ⚠️ Já existiam: {result.get('already_exists_count', 0)}")
        print(f"   ❌ Erros: {result.get('error_count', 0)}")
    else:
        print(f"❌ Erro na pré-população: {prepopulate_response.status_code}")
        print(prepopulate_response.text)
        return

    # 3. Verifica estatísticas finais
    print(f"\n📊 Verificando estatísticas finais...")
    final_stats_response = requests.get(f"{BASE_URL}/prepopulate/stats")

    if final_stats_response.status_code == 200:
        final_stats = final_stats_response.json()
        print(f"   📈 Filmes: {final_stats.get('total_movies', 0)}")
        print(f"   🎭 Diretores: {final_stats.get('total_directors', 0)}")
        print(f"   🎵 Trilhas sonoras: {final_stats.get('total_soundtracks', 0)}")
        print(f"   📊 Cobertura geral: {final_stats.get('overall_coverage', 0)}%")

        # Calcula melhorias
        if stats_response.status_code == 200:
            initial_stats = stats_response.json()
            director_improvement = final_stats.get(
                "total_directors", 0
            ) - initial_stats.get("total_directors", 0)
            soundtrack_improvement = final_stats.get(
                "total_soundtracks", 0
            ) - initial_stats.get("total_soundtracks", 0)

            print(f"\n📈 MELHORIAS:")
            print(f"   🎭 Novos diretores: +{director_improvement}")
            print(f"   🎵 Novas trilhas sonoras: +{soundtrack_improvement}")

    total_time = time.time() - start_time
    print(f"\n⏱️ TEMPO TOTAL: {total_time:.2f}s")
    print("🎉 Processamento concluído!")


def test_movie_detail_performance():
    """Testa performance após pré-população"""

    print(f"\n🧪 Testando performance após pré-população...")
    print("=" * 50)

    # Testa com um filme específico
    movie_id = "tt0060304"

    # Limpa cache para testar
    requests.post(
        f"{BASE_URL}/movie-detail/{movie_id}/invalidate", json={"language": "pt"}
    )

    # Teste de performance
    start_time = time.time()
    response = requests.get(f"{BASE_URL}/movie-detail/{movie_id}?language=pt")
    request_time = time.time() - start_time

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Sucesso! Tempo: {request_time:.2f}s")
        print(f"💾 Cache usado: {data.get('from_cache', False)}")
        print(f"🎬 Filme: {data.get('movie', {}).get('title', 'N/A')}")
        print(f"🎭 Diretor: {data.get('director', {}).get('name', 'N/A')}")
        print(
            f"🎵 Trilha sonora: {len(data.get('soundtrack', {}).get('tracks', []))} músicas"
        )

        if request_time < 0.5:
            print("🚀 Performance excelente!")
        elif request_time < 1.0:
            print("✅ Performance boa!")
        else:
            print("⚠️ Performance pode ser melhorada")
    else:
        print(f"❌ Erro: {response.status_code}")


if __name__ == "__main__":
    try:
        process_all_existing_movies()
        test_movie_detail_performance()
    except requests.exceptions.ConnectionError:
        print("❌ Erro: Não foi possível conectar ao servidor.")
        print("Certifique-se de que o backend está rodando em http://localhost:5001")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
