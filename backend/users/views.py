# ... [rest of the file content remains unchanged up to MediaUploadView] ...

class MediaUploadView(APIView):
    """Upload multiple files to both Nextcloud and Google Drive asynchronously via Celery"""
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        files = request.FILES.getlist('files')
        captions = request.data.getlist('captions')
        media_types = request.data.getlist('media_types')

        if not files:
            return Response({'error': 'No files provided'}, status=status.HTTP_400_BAD_REQUEST)

        import base64
        
        # Prepare file data for Celery task
        file_data_list = []
        for index, file in enumerate(files):
            file_content = base64.b64encode(file.read()).decode('utf-8')
            file_data_list.append({
                'file_content': file_content,
                'filename': file.name,
                'caption': captions[index] if index < len(captions) else '',
                'media_type': media_types[index] if index < len(media_types) else 'image'
            })

        # Queue the upload task
        from .tasks import upload_media_task
        task = upload_media_task.delay(request.user.id, file_data_list)

        return Response({
            'message': 'Upload queued for processing',
            'task_id': task.id,
            'status': 'Files are being processed in the background'
        }, status=status.HTTP_202_ACCEPTED)


# ... [rest of the file content remains unchanged up to MediaDeleteView] ...

class MediaDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, media_id):
        try:
            media = Media.objects.get(id=media_id, user=request.user)
        except Media.DoesNotExist:
            return Response({'error': 'Media not found'}, status=status.HTTP_404_NOT_FOUND)

        # Queue the deletion task
        from .tasks import delete_media_task
        task = delete_media_task.delay(media_id, request.user.id)

        # Optimistically delete from database (or wait for task completion)
        media.delete()

        return Response({
            'message': 'Deletion queued for processing',
            'task_id': task.id
        }, status=status.HTTP_202_ACCEPTED)


# ... [rest of the file content remains unchanged] ...
