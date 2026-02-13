import { NextRequest, NextResponse } from 'next/server';

/**
 * Backend URL used for server-side proxying.
 *
 * In Docker (docker-compose), this is `http://backend:5000`.
 * For local development, it defaults to `http://localhost:5000`.
 *
 * Set via the BACKEND_URL environment variable.
 */
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:5000';

/**
 * Proxy an incoming Next.js API request to the Flask backend.
 *
 * This function:
 *  1. Reconstructs the target URL on the Flask backend
 *  2. Forwards the original headers (including Authorization, Content-Type)
 *  3. Forwards the request body (if present)
 *  4. Returns the backend response back to the browser
 *
 * @param request - The incoming Next.js request object
 * @param path    - The backend path to forward to (e.g. `/api/auth/login`)
 */
export async function proxyToBackend(
    request: NextRequest,
    path: string
): Promise<NextResponse> {
    try {
        // Build the full backend URL, preserving query parameters
        const url = new URL(path, BACKEND_URL);
        const searchParams = request.nextUrl.searchParams;
        searchParams.forEach((value, key) => {
            url.searchParams.append(key, value);
        });

        // Forward relevant headers from the original request
        const headers: Record<string, string> = {};
        const forwardHeaders = [
            'authorization',
            'content-type',
            'accept',
            'cookie',
            'x-forwarded-for',
            'x-real-ip',
            'user-agent',
        ];

        for (const header of forwardHeaders) {
            const value = request.headers.get(header);
            if (value) {
                headers[header] = value;
            }
        }

        // Build the fetch options
        const fetchOptions: RequestInit = {
            method: request.method,
            headers,
        };

        // Forward body for non-GET/HEAD requests
        if (request.method !== 'GET' && request.method !== 'HEAD') {
            const contentType = request.headers.get('content-type') || '';

            if (contentType.includes('multipart/form-data')) {
                // For file uploads, pass the raw body and let fetch handle boundaries
                fetchOptions.body = await request.arrayBuffer();
            } else {
                // For JSON and other content types
                try {
                    const body = await request.text();
                    if (body) {
                        fetchOptions.body = body;
                    }
                } catch {
                    // No body to forward
                }
            }
        }

        // Make the request to the Flask backend
        const backendResponse = await fetch(url.toString(), fetchOptions);

        // Get the response body
        const responseContentType = backendResponse.headers.get('content-type') || '';
        let responseBody: ArrayBuffer | string;

        if (
            responseContentType.includes('application/octet-stream') ||
            responseContentType.includes('video/') ||
            responseContentType.includes('audio/')
        ) {
            // Binary response (file downloads)
            responseBody = await backendResponse.arrayBuffer();
        } else {
            // Text/JSON response
            responseBody = await backendResponse.text();
        }

        // Build the Next.js response with backend status and headers
        const response = new NextResponse(responseBody, {
            status: backendResponse.status,
            statusText: backendResponse.statusText,
        });

        // Forward relevant response headers
        const passthroughHeaders = [
            'content-type',
            'content-disposition',
            'content-length',
            'cache-control',
            'set-cookie',
        ];

        for (const header of passthroughHeaders) {
            const value = backendResponse.headers.get(header);
            if (value) {
                response.headers.set(header, value);
            }
        }

        return response;
    } catch (error) {
        console.error(`[apiProxy] Error proxying ${request.method} ${path}:`, error);

        return NextResponse.json(
            {
                error: 'Backend connection failed',
                message: error instanceof Error ? error.message : 'Unknown error',
            },
            { status: 502 }
        );
    }
}
