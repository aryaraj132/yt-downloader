import { NextRequest } from 'next/server';
import { proxyToBackend } from '@/lib/apiProxy';

export async function GET(
    request: NextRequest,
    { params }: { params: { path: string[] } }
) {
    const path = `/api/public/${params.path.join('/')}`;
    return proxyToBackend(request, path);
}

export async function POST(
    request: NextRequest,
    { params }: { params: { path: string[] } }
) {
    const path = `/api/public/${params.path.join('/')}`;
    return proxyToBackend(request, path);
}

export async function PUT(
    request: NextRequest,
    { params }: { params: { path: string[] } }
) {
    const path = `/api/public/${params.path.join('/')}`;
    return proxyToBackend(request, path);
}

export async function DELETE(
    request: NextRequest,
    { params }: { params: { path: string[] } }
) {
    const path = `/api/public/${params.path.join('/')}`;
    return proxyToBackend(request, path);
}

export async function PATCH(
    request: NextRequest,
    { params }: { params: { path: string[] } }
) {
    const path = `/api/public/${params.path.join('/')}`;
    return proxyToBackend(request, path);
}
