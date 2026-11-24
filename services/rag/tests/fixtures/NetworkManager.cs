// NetworkManager.cs — fixture de teste (não é código do DiceVTT).
// Cabeçalho: gerencia a sessão de rede fictícia.
using System;
using UnityEngine;

namespace Fixture.Net
{
    [Serializable]
    internal class Helper { }

    /// <summary>
    /// Gerencia lobbies Steamworks e a sincronização P2P dos tokens.
    /// Usa <see cref="LobbyData"/> para guardar o estado.
    /// </summary>
    [DisallowMultipleComponent]
    public sealed partial class NetworkManager : MonoBehaviour
    {
        private const string Fake = "class NotAClass { }";
        private string verbatim = @"public class AlsoNot ""quoted""";
        private string raw = """
            class InsideRaw { }
            """;

        // comentário interno que não deve entrar no resumo
        public void CriarLobby()
        {
            var x = $"interpolado {Fake} class Nope";
            Debug.Log(x);
        }
    }
}
