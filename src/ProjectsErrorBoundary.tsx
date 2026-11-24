import { Component, type ReactNode } from 'react';

// A rendering failure must not remove the navigation or leave a blank screen.
// Recovery remounts the read-only initial view; it never retries a submitted action.
export default class ProjectsErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() {
    if (!this.state.failed) return this.props.children;
    return <section className="panel projects-conversation" role="alert">
      <h1>Não foi possível exibir esta conversa</h1>
      <p>Ocorreu um erro na interface. Volte à lista e consulte o estado do pedido antes de enviá-lo novamente. Esta recuperação não reenvia pedidos nem aprova planos.</p>
      <button type="button" className="button" onClick={() => this.setState({ failed: false })}>Voltar às conversas</button>
    </section>;
  }
}
